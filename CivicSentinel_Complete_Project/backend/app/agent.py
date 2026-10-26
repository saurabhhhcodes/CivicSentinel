import os, json, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Job, Asset, Alert, Incident, AuditLog, Camera
from .vision import analyze_water_and_obstruction
from .location_service import resolve_camera_and_authority, resolve_asset_and_authority
from .risk_engine import evaluate_temporal_risk
from .notification_service import notification_service

class AgenticInvestigationPipeline:
    """
    Agentic visual infrastructure investigation state machine:
    OBSERVE -> ASSESS_EVIDENCE_QUALITY -> INSPECT_ROI -> TEMPORAL_COMPARISON ->
    RISK_TRIAGE -> RESOLVE_AUTHORITY -> DISPATCH_INCIDENT -> UPDATE_DIGITAL_TWIN.
    """
    def __init__(self, db: Session, job: Job, metrics: dict, evidence_files: list[str], camera_id: str | None = None, asset_hint: str | None = None):
        self.db = db
        self.job = job
        self.metrics = metrics
        self.evidence_files = evidence_files
        self.camera_id = camera_id
        self.asset_hint = asset_hint
        self.trace = []
        self.step_counter = 1

    def _record_step(self, state: str, tool: str, decision: str, inputs: dict, result: any):
        step_entry = {
            "step": self.step_counter,
            "state": state,
            "tool": tool,
            "decision": decision,
            "inputs": inputs,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.trace.append(step_entry)
        self.step_counter += 1
        return result

    def run(self) -> dict:
        # Step 1: OBSERVE
        water_ratio = self.metrics.get("water_area_ratio_proxy", 0.0)
        conf = self.metrics.get("visual_confidence", 0.0)
        self._record_step(
            state="OBSERVE",
            tool="opencv_pipeline",
            decision="Ingest and process media frames using multi-band HSV and morphological filtering.",
            inputs={"filename": self.job.filename, "media_type": self.job.media_type},
            result={
                "water_area_ratio_proxy": water_ratio,
                "candidate_regions": self.metrics.get("candidate_region_count", 0),
                "visual_confidence": conf
            }
        )

        # Step 2: ASSESS_EVIDENCE_QUALITY
        q_metrics = self.metrics.get("quality_metrics", {})
        q_label = self.metrics.get("image_quality", "acceptable")
        self._record_step(
            state="ASSESS_EVIDENCE_QUALITY",
            tool="evaluate_image_quality",
            decision="Verify illumination, focus blur (Laplacian variance), and texture before decision-making.",
            inputs={"quality_metrics": q_metrics},
            result={
                "quality_label": q_label,
                "sharpness_score": q_metrics.get("sharpness_score"),
                "issues_detected": q_metrics.get("quality_issues", [])
            }
        )

        # Step 3: INSPECT_ROI & OBSTRUCTION ASSESSMENT
        obs_idx = self.metrics.get("obstruction_index_proxy", 0.0)
        obs_suspected = self.metrics.get("obstruction_suspected", False)
        self._record_step(
            state="INSPECT_ROI",
            tool="assess_obstruction",
            decision="Inspect drainage intake perimeter for floating debris or physical blockage indicators.",
            inputs={"candidate_regions": self.metrics.get("candidate_region_count", 0)},
            result={
                "obstruction_suspected": obs_suspected,
                "obstruction_index": obs_idx,
                "debris_edge_density": obs_idx
            }
        )

        # Step 4: TEMPORAL_COMPARISON
        trend = self.metrics.get("temporal_trend", "insufficient_observations")
        acc_rate = self.metrics.get("accumulation_rate_percent_per_min", 0.0)
        self._record_step(
            state="TEMPORAL_COMPARISON",
            tool="compare_observations",
            decision="Measure rate of change across sampled frames to determine whether hazard is accelerating.",
            inputs={"frames_processed": self.metrics.get("frames_processed", 1), "temporal_trend": trend},
            result={
                "temporal_trend": trend,
                "temporal_delta": self.metrics.get("temporal_change", 0.0),
                "accumulation_rate_percent_per_min": acc_rate
            }
        )

        # Step 5: RISK_TRIAGE
        risk = evaluate_temporal_risk(
            water_area_ratio=water_ratio,
            temporal_trend=trend,
            accumulation_rate=acc_rate,
            obstruction_index=obs_idx,
            visual_confidence=conf,
            image_quality=q_label
        )
        self._record_step(
            state="RISK_TRIAGE",
            tool="calculate_risk",
            decision="Synthesize visual proxy, accumulation velocity, and obstruction heuristics into operational risk tier.",
            inputs={"composite_score": risk["risk_score"], "current_risk": risk["current_risk"]},
            result=risk
        )

        # Step 6: RESOLVE_LOCATION_AUTHORITY
        location_data = resolve_camera_and_authority(
            self.db,
            camera_id=self.camera_id,
            asset_hint=self.asset_hint
        )
        asset_id = location_data["asset_id"]
        auth_info = location_data["authority"]
        loc_verified = location_data.get("location_verification_status") == "VERIFIED"
        
        self._record_step(
            state="RESOLVE_LOCATION_AUTHORITY",
            tool="resolve_camera_location",
            decision="Resolve verified infrastructure coordinates and responsible municipal authority without using personal device location.",
            inputs={"camera_id": self.camera_id, "asset_id": asset_id, "ward": location_data["ward"]},
            result={
                "camera_id": location_data.get("camera_id"),
                "asset_name": location_data["asset_name"],
                "coordinates": f"{location_data['latitude']}, {location_data['longitude']}",
                "ward": location_data["ward"],
                "department": location_data["department"],
                "verification_status": location_data.get("location_verification_status"),
                "assigned_authority": auth_info["name"] if auth_info else "UNASSIGNED"
            }
        )

        # Step 7: INCIDENT_DISPATCH & NOTIFICATION
        incident = None
        notif_result = None
        now_utc = datetime.now(timezone.utc)
        now_iso = now_utc.isoformat()

        # If risk is elevated (MEDIUM, HIGH, CRITICAL, or UNKNOWN needing inspection), manage incident
        if risk["current_risk"] in ("MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"):
            # Check for existing open incident for this asset / camera (Deduplication & Cooldown)
            sev_levels = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
            active_statuses = ["DETECTED", "VALIDATED", "NOTIFICATION_PENDING", "NOTIFIED", "ACKNOWLEDGED", "ACTION_IN_PROGRESS", "ESCALATED"]
            
            existing_incident = self.db.scalars(
                select(Incident).where(
                    Incident.asset_id == asset_id,
                    Incident.status.in_(active_statuses)
                ).order_by(Incident.created_at.desc())
            ).first()

            # If existing incident is recent and severity has not escalated, update rather than spawn duplicate
            is_escalation = (
                existing_incident is not None and
                sev_levels.get(risk["current_risk"], 0) > sev_levels.get(existing_incident.severity, 0)
            )

            if existing_incident and not is_escalation:
                # Deduplication: update existing incident
                existing_incident.trigger_evidence = json.dumps({"evidence_images": self.evidence_files, "metrics": self.metrics})
                existing_incident.risk_score = risk["risk_score"]
                existing_incident.risk_explanation = "; ".join(risk["reasons"])
                existing_incident.updated_at = now_iso
                
                trail = json.loads(existing_incident.audit_trail or "[]")
                trail.append({
                    "timestamp": now_iso,
                    "action": "TELEMETRY_UPDATED_DEDUPLICATED",
                    "actor": "AGENTIC_VISION_PIPELINE",
                    "job_id": self.job.id,
                    "water_ratio": water_ratio
                })
                existing_incident.audit_trail = json.dumps(trail)
                self.db.commit()
                incident = existing_incident

                self._record_step(
                    state="DISPATCH_INCIDENT",
                    tool="deduplicate_incident",
                    decision="Active incident already in progress for this monitored infrastructure. Telemetry updated without duplicate alert dispatch.",
                    inputs={"incident_id": incident.id, "current_severity": incident.severity},
                    result={"incident_id": incident.id, "action": "UPDATED_EXISTING"}
                )
            else:
                inc_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
                delay_minutes = (auth_info["critical_delay_minutes"] if auth_info else 5) if risk["current_risk"] == "CRITICAL" else (auth_info["escalation_delay_minutes"] if auth_info else 15)
                ack_deadline = (now_utc + timedelta(minutes=delay_minutes)).isoformat() if loc_verified else None

                initial_status = "NOTIFICATION_PENDING" if (loc_verified and auth_info and auth_info.get("level_1_email")) else "UNDER_REVIEW"
                assigned_dept = auth_info["department"] if (loc_verified and auth_info) else "UNASSIGNED"
                assigned_email = auth_info["level_1_email"] if (loc_verified and auth_info) else None
                assigned_auth_id = auth_info["authority_id"] if (loc_verified and auth_info) else None

                incident = Incident(
                    id=inc_id,
                    asset_id=asset_id,
                    camera_id=location_data.get("camera_id"),
                    job_id=self.job.id,
                    severity=risk["current_risk"],
                    status=initial_status,
                    location_verification_status=location_data.get("location_verification_status", "VERIFIED"),
                    road_landmark=location_data.get("road_landmark"),
                    zone=location_data.get("zone"),
                    district=location_data.get("district"),
                    delivery_status="READY_TO_SEND" if loc_verified else "NEW",
                    trigger_evidence=json.dumps({"evidence_images": self.evidence_files, "metrics": self.metrics}),
                    temporal_trend=trend,
                    risk_score=risk["risk_score"],
                    risk_explanation="; ".join(risk["reasons"]),
                    recommended_action=risk["recommended_action"],
                    assigned_authority_id=assigned_auth_id,
                    assigned_department=assigned_dept,
                    assigned_contact_email=assigned_email,
                    acknowledgement_deadline=ack_deadline,
                    escalation_level=1 if loc_verified else 0,
                    created_at=now_iso,
                    updated_at=now_iso,
                    audit_trail=json.dumps([{
                        "timestamp": now_iso,
                        "action": "INCIDENT_CREATED",
                        "actor": "AGENTIC_VISION_PIPELINE",
                        "severity": risk["current_risk"],
                        "job_id": self.job.id,
                        "verification_status": location_data.get("location_verification_status", "VERIFIED")
                    }])
                )
                self.db.add(incident)
                self.db.commit()

                # Dispatch Notification ONLY if location and authority are verified
                if loc_verified and assigned_email:
                    notif_result = notification_service.send_incident_notification(
                        db=self.db,
                        incident=incident,
                        asset_data=location_data,
                        recipient_email=assigned_email,
                        recipient_role=f"Field Response / {auth_info.get('level_1_name', 'Field Unit')}",
                        level=1
                    )
                    incident.status = "NOTIFIED" if notif_result.get("status") in ("SENT", "SIMULATED") else "NOTIFICATION_FAILED"
                    self.db.commit()

                    self._record_step(
                        state="DISPATCH_INCIDENT",
                        tool="send_incident_notification",
                        decision="Persist incident record and transmit authenticated dispatch with acknowledgement token to verified authority.",
                        inputs={
                            "incident_id": inc_id,
                            "recipient": assigned_email,
                            "deadline_minutes": delay_minutes
                        },
                        result={
                            "incident_id": inc_id,
                            "notification_status": notif_result.get("status"),
                            "channel": notif_result.get("channel"),
                            "acknowledgement_deadline": ack_deadline
                        }
                    )
                else:
                    # Unverified location or missing authority: mark UNASSIGNED for review
                    self._record_step(
                        state="DISPATCH_INCIDENT",
                        tool="review_unverified_location",
                        decision="Location or authority unverified. Auto-notification halted; marked UNASSIGNED for administrative verification.",
                        inputs={"incident_id": inc_id, "verification_status": location_data.get("location_verification_status")},
                        result={"incident_id": inc_id, "status": "UNDER_REVIEW", "assignment": "UNASSIGNED"}
                    )

                # Backward-compatible Alert record for existing frontend
                self.db.add(Alert(
                    id=f"ALT-{uuid.uuid4().hex[:10].upper()}",
                    job_id=self.job.id,
                    asset_id=asset_id,
                    severity=risk["current_risk"],
                    status="PENDING_REVIEW",
                    summary="; ".join(risk["reasons"])
                ))

        # Step 8: UPDATE_DIGITAL_TWIN
        asset_record = self.db.get(Asset, asset_id)
        if asset_record:
            asset_record.current_risk = risk["current_risk"]
            asset_record.latest_job_id = self.job.id
            asset_record.summary = json.dumps({
                "risk": risk,
                "trend": trend,
                "latest_incident_id": incident.id if incident else None,
                "last_inspected": now_iso
            })
            self.db.commit()

        self._record_step(
            state="UPDATE_DIGITAL_TWIN",
            tool="update_digital_twin",
            decision="Update spatial digital twin state, risk status, and latest telemetry for asset.",
            inputs={"asset_id": asset_id, "current_risk": risk["current_risk"]},
            result={"asset_id": asset_id, "status": "SYNCHRONIZED"}
        )

        return {
            "risk": risk,
            "agent": {
                "agent_status": "NEEDS_REVIEW" if risk["human_review_required"] else "COMPLETED",
                "trace": self.trace,
                "recommendation": risk["recommended_action"],
                "incident_id": incident.id if incident else None,
                "location": location_data
            },
            "asset_id": asset_id,
            "evidence_images": self.evidence_files
        }
