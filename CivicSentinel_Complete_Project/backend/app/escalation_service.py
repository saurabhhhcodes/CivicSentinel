import os, json, logging, uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from .models import Incident, AuthorityConfig, Asset, AuditLog, SessionLocal
from .notification_service import notification_service
from .location_service import resolve_asset_and_authority

logger = logging.getLogger("civicsentinel.escalation")

def process_pending_escalations(db: Session) -> list[dict]:
    """
    Check all unacknowledged and active incidents for overdue escalation deadlines.
    Recovers seamlessly on server restart by querying the persistent database.
    """
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.isoformat()

    # Incidents subject to escalation:
    # Status is NOTIFIED or ESCALATED, not acknowledged yet, and deadline is in the past
    escalatable_statuses = ["NOTIFIED", "ESCALATION_PENDING", "ESCALATED"]
    
    query = select(Incident).where(
        Incident.status.in_(escalatable_statuses),
        Incident.acknowledged_at.is_(None),
        Incident.resolved_at.is_(None),
        Incident.acknowledgement_deadline.isnot(None),
        Incident.acknowledgement_deadline <= now_iso,
        Incident.escalation_level < 3  # Max level 3
    )

    overdue_incidents = db.scalars(query).all()
    results = []

    for inc in overdue_incidents:
        asset_info = resolve_asset_and_authority(db, asset_hint=inc.asset_id)
        auth = asset_info["authority"]
        
        current_level = inc.escalation_level or 1
        next_level = current_level + 1

        recipient_email = None
        recipient_role = None

        if next_level == 2:
            recipient_email = auth["level_2_email"]
            recipient_role = f"District Supervisor / {auth['level_2_name']}"
            delay_minutes = auth["escalation_delay_minutes"]
        elif next_level >= 3:
            recipient_email = auth["level_3_email"]
            recipient_role = f"Municipal Control Room / {auth['level_3_name']}"
            delay_minutes = auth["escalation_delay_minutes"]
            next_level = 3

        if not recipient_email:
            continue

        # Calculate new escalation deadline
        next_deadline = (now_utc + timedelta(minutes=delay_minutes)).isoformat()
        
        # Dispatch escalation notification
        notif_result = notification_service.send_incident_notification(
            db=db,
            incident=inc,
            asset_data=asset_info,
            recipient_email=recipient_email,
            recipient_role=recipient_role,
            level=next_level
        )

        # Update incident record
        inc.escalation_level = next_level
        inc.status = "ESCALATED"
        inc.delivery_status = "SENT" if notif_result.get("status") == "SENT" else ("SIMULATED" if notif_result.get("status") == "SIMULATED" else "DELIVERY_FAILED")
        inc.assigned_contact_email = recipient_email
        inc.escalated_at = now_iso
        inc.acknowledgement_deadline = next_deadline
        inc.updated_at = now_iso

        # Append to audit trail
        trail = json.loads(inc.audit_trail or "[]")
        trail.append({
            "timestamp": now_iso,
            "action": f"AUTOMATIC_ESCALATION_LEVEL_{next_level}",
            "recipient": recipient_email,
            "role": recipient_role,
            "reason": f"Level {current_level} unacknowledged after deadline.",
            "notification_audit_id": notif_result.get("audit_id"),
            "delivery_status": inc.delivery_status
        })
        inc.audit_trail = json.dumps(trail)

        # Record system audit log
        db.add(AuditLog(
            id=f"AUD-{inc.id}-L{next_level}-{uuid.uuid4().hex[:6]}",
            entity_type="INCIDENT",
            entity_id=inc.id,
            action=f"ESCALATE_LEVEL_{next_level}",
            actor="SYSTEM_SCHEDULER",
            details_json=json.dumps({"recipient": recipient_email, "level": next_level, "deadline": next_deadline})
        ))

        db.commit()

        results.append({
            "incident_id": inc.id,
            "new_level": next_level,
            "recipient": recipient_email,
            "new_deadline": next_deadline,
            "status": notif_result.get("status")
        })

    return results

def acknowledge_incident_by_token(db: Session, incident_id: str, token: str, actor_note: str = "Email Link Acknowledgement") -> dict:
    """
    Authenticate and record an incident acknowledgement via secure token.
    Halts pending escalation.
    """
    inc = db.get(Incident, incident_id)
    if not inc:
        return {"success": False, "status_code": 404, "message": "Incident not found."}

    if inc.status in ("RESOLVED", "REJECTED_AS_FALSE_ALARM"):
        return {"success": False, "status_code": 409, "message": f"Incident is already closed ({inc.status})."}

    if inc.acknowledged_at:
        return {"success": True, "already_acknowledged": True, "message": f"Incident {incident_id} was already acknowledged at {inc.acknowledged_at}."}

    # Verify token
    if not inc.acknowledgement_token or inc.acknowledgement_token != token:
        return {"success": False, "status_code": 403, "message": "Invalid or expired acknowledgement token."}

    now_iso = datetime.now(timezone.utc).isoformat()
    inc.status = "ACKNOWLEDGED"
    inc.delivery_status = "ACKNOWLEDGED"
    inc.acknowledged_at = now_iso
    inc.acknowledged_by = actor_note
    inc.acknowledgement_deadline = None  # Halt escalation countdown
    inc.updated_at = now_iso

    # Append to audit trail
    trail = json.loads(inc.audit_trail or "[]")
    trail.append({
        "timestamp": now_iso,
        "action": "INCIDENT_ACKNOWLEDGED",
        "actor": actor_note,
        "note": "Escalation paused. Field team or supervisor confirmed receipt."
    })
    inc.audit_trail = json.dumps(trail)

    db.add(AuditLog(
        id=f"AUD-{inc.id}-ACK",
        entity_type="INCIDENT",
        entity_id=inc.id,
        action="ACKNOWLEDGE",
        actor=actor_note,
        details_json=json.dumps({"timestamp": now_iso})
    ))
    db.commit()

    return {
        "success": True,
        "incident_id": inc.id,
        "status": inc.status,
        "acknowledged_at": inc.acknowledged_at,
        "message": "Incident acknowledged successfully. Automated escalation has been halted."
    }
