import os, json, time, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import cv2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.main import app, process_job_pipeline
from backend.app.models import SessionLocal, Job, Incident, Asset, AuthorityConfig, NotificationAudit, Alert, init_db
from backend.app.vision import evaluate_image_quality, analyze_water_and_obstruction, process_image_media, decode_image_buffer
from backend.app.risk_engine import evaluate_temporal_risk
from backend.app.location_service import resolve_asset_and_authority, calculate_haversine_km
from backend.app.notification_service import notification_service, build_incident_email_content, generate_acknowledgement_token
from backend.app.escalation_service import process_pending_escalations, acknowledge_incident_by_token
from backend.app.aws_service import aws_service
from backend.app.benchmark_service import run_opencv_benchmark

init_db()
client = TestClient(app)

# -------------------------------------------------------------
# Test A & D: Image & Video Processing & Evidence Persistence
# -------------------------------------------------------------
def test_real_image_processing_and_evidence(tmp_path):
    # Create realistic test image with ponding
    h, w = 240, 320
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:, :] = (35, 45, 55)
    # Draw ponding area (dark reflective water)
    cv2.circle(img, (160, 140), 50, (15, 15, 15), -1)
    
    test_img_path = tmp_path / "test_pond.jpg"
    cv2.imwrite(str(test_img_path), img)

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(exist_ok=True)

    metrics, evidence_files = process_image_media(test_img_path, evidence_dir, "job_test_01")
    assert metrics["water_area_ratio_proxy"] > 0
    assert len(evidence_files) == 1
    assert (evidence_dir / evidence_files[0]).is_file()
    assert (evidence_dir / evidence_files[0]).stat().st_size > 0

# -------------------------------------------------------------
# Test B: Invalid & Corrupted Uploads
# -------------------------------------------------------------
def test_upload_corrupt_signature():
    # Bad extension
    r1 = client.post("/api/uploads", files={"file": ("malicious.sh", b"echo hello", "text/plain")})
    assert r1.status_code == 415

    # Valid extension but invalid binary signature
    r2 = client.post("/api/uploads", files={"file": ("fake.jpg", b"not-a-jpeg-header", "image/jpeg")})
    assert r2.status_code == 415

# -------------------------------------------------------------
# Test E, F & G: Temporal Risk Calculations & Unknown Insufficient Evidence
# -------------------------------------------------------------
def test_temporal_risk_categories():
    # Critical risk: high water ratio + increasing trend
    crit = evaluate_temporal_risk(
        water_area_ratio=0.65,
        temporal_trend="increasing",
        accumulation_rate=6.5,
        obstruction_index=0.5,
        visual_confidence=0.85,
        image_quality="acceptable"
    )
    assert crit["current_risk"] == "CRITICAL"
    assert crit["human_review_required"] is True

    # High risk
    high = evaluate_temporal_risk(
        water_area_ratio=0.40,
        temporal_trend="stable",
        accumulation_rate=0.0,
        obstruction_index=0.2,
        visual_confidence=0.75,
        image_quality="acceptable"
    )
    assert high["current_risk"] == "HIGH"

    # Low risk
    low = evaluate_temporal_risk(
        water_area_ratio=0.05,
        temporal_trend="decreasing",
        accumulation_rate=-2.0,
        obstruction_index=0.05,
        visual_confidence=0.80,
        image_quality="acceptable"
    )
    assert low["current_risk"] == "LOW"

    # Degraded / Low Confidence -> UNKNOWN (Never claims safe)
    unk = evaluate_temporal_risk(
        water_area_ratio=0.01,
        temporal_trend="insufficient_observations",
        accumulation_rate=0.0,
        obstruction_index=0.0,
        visual_confidence=0.20,  # Below threshold
        image_quality="poor"
    )
    assert unk["current_risk"] == "UNKNOWN"
    assert unk["human_review_required"] is True
    assert "UNKNOWN status does not imply absence of risk" in unk["reasons"][1]

# -------------------------------------------------------------
# Test I & J: Asset Location Resolution & Authority Assignment
# -------------------------------------------------------------
def test_location_and_authority_resolution():
    with SessionLocal() as db:
        res = resolve_asset_and_authority(db, asset_hint="ASSET-W4-CULVERT12")
        assert res["asset_id"] == "ASSET-W4-CULVERT12"
        assert res["ward"] == "Ward 4"
        assert res["latitude"] is not None
        assert res["authority"]["authority_id"] == "AUTH-WARD-04"
        assert res["authority"]["level_1_email"] != ""
        assert res["authority"]["level_2_email"] != ""
        assert res["authority"]["level_3_email"] != ""

def test_haversine_distance():
    d = calculate_haversine_km(12.9716, 77.5946, 12.9740, 77.5980)
    assert 0.3 < d < 0.6  # Approx 450 meters

# -------------------------------------------------------------
# Test K, L, M & N: Incident Creation, Email Generation & Idempotency
# Test O & Y: Secure Acknowledgement by Token (combined for shared state)
# -------------------------------------------------------------
def test_incident_creation_notification_and_ack():
    """Unified test: create incident, notify, then securely acknowledge via token."""
    inc_id = "INC-NOTIF-" + uuid.uuid4().hex[:8].upper()
    with SessionLocal() as db:
        now_iso = datetime.now(timezone.utc).isoformat()
        inc = Incident(
            id=inc_id,
            asset_id="ASSET-W4-CULVERT12",
            job_id="job-unit-" + uuid.uuid4().hex[:6],
            severity="HIGH",
            status="NOTIFICATION_PENDING",
            temporal_trend="increasing",
            risk_score=0.72,
            risk_explanation="Ponding expanding near main culvert intake.",
            recommended_action="Dispatch Ward 4 drainage crew.",
            assigned_authority_id="AUTH-WARD-04",
            assigned_department="Municipal Stormwater",
            assigned_contact_email="ward4-test@city.local",
            escalation_level=1,
            acknowledgement_deadline=(datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
            created_at=now_iso,
            updated_at=now_iso
        )
        db.add(inc)
        db.commit()

        # Get DB-bound instance after add
        db_inc = db.get(Incident, inc_id)
        assert db_inc is not None

        asset_data = resolve_asset_and_authority(db, asset_hint=db_inc.asset_id)

        # Test notification dispatch in mock mode (no real email sent)
        res = notification_service.send_incident_notification(
            db=db,
            incident=db_inc,
            asset_data=asset_data,
            recipient_email="ward4-test@city.local",
            recipient_role="Field Response Crew",
            level=1
        )
        assert res["status"] in ("SENT", "SIMULATED")
        assert "token=" in res["ack_url"]

        # Verify token was persisted to DB
        db.expire_all()
        db_inc2 = db.get(Incident, inc_id)
        assert db_inc2 is not None
        assert db_inc2.acknowledgement_token is not None
        token = db_inc2.acknowledgement_token

        # Verify notification audit entry was written
        audit = db.scalars(select(NotificationAudit).where(NotificationAudit.incident_id == inc_id)).first()
        assert audit is not None
        assert audit.recipient == "ward4-test@city.local"
        assert audit.level == 1

        # --- Acknowledgement via secure token ---

        # Invalid token must be rejected (403)
        bad_res = acknowledge_incident_by_token(db, inc_id, "bogus-invalid-token")
        assert bad_res["success"] is False
        assert bad_res["status_code"] == 403

        # Valid token must succeed
        good_res = acknowledge_incident_by_token(db, inc_id, token, actor_note="Field Supervisor Mobile Ack")
        assert good_res["success"] is True
        assert good_res["incident_id"] == inc_id

        # Verify DB state after acknowledgement
        db.expire_all()
        final_inc = db.get(Incident, inc_id)
        assert final_inc.status == "ACKNOWLEDGED"
        assert final_inc.acknowledged_at is not None
        assert final_inc.acknowledgement_deadline is None  # Escalation halted

        # Idempotent replay must safely return already_acknowledged
        replay_res = acknowledge_incident_by_token(db, inc_id, token)
        assert replay_res["success"] is True
        assert replay_res.get("already_acknowledged") is True

# -------------------------------------------------------------
# Test P, Q & R: Automatic Escalation Deadlines, Restart Recovery & Duplicate Prevention
# -------------------------------------------------------------
def test_automatic_escalation_flow():
    inc_id = "INC-ESC-" + uuid.uuid4().hex[:8].upper()
    with SessionLocal() as db:
        now_utc = datetime.now(timezone.utc)
        past_deadline = (now_utc - timedelta(minutes=5)).isoformat()

        inc = Incident(
            id=inc_id,
            asset_id="ASSET-W4-CULVERT12",
            job_id="job-esc-" + uuid.uuid4().hex[:6],
            severity="CRITICAL",
            status="NOTIFIED",
            temporal_trend="increasing",
            risk_score=0.92,
            risk_explanation="Critical intake blockage detected.",
            recommended_action="Emergency clearance required.",
            assigned_authority_id="AUTH-WARD-04",
            assigned_department="Municipal Stormwater",
            assigned_contact_email="ward4-test@city.local",
            escalation_level=1,
            acknowledgement_deadline=past_deadline,
            acknowledged_at=None,
            created_at=(now_utc - timedelta(minutes=20)).isoformat(),
            updated_at=(now_utc - timedelta(minutes=20)).isoformat()
        )
        db.add(inc)
        db.commit()
        db.expire_all()

        # Run escalation worker tick — must escalate this overdue incident
        escalated_list = process_pending_escalations(db)
        matching = [e for e in escalated_list if e["incident_id"] == inc_id]
        assert len(matching) == 1
        assert matching[0]["new_level"] == 2  # Escalated to Level 2 (Supervisor)

        # Re-query from DB — deadline now in the future
        updated_inc = db.get(Incident, inc_id)
        assert updated_inc.status == "ESCALATED"
        assert updated_inc.escalation_level == 2
        assert updated_inc.escalated_at is not None
        assert updated_inc.acknowledgement_deadline > past_deadline

        # Second tick must NOT re-escalate (deadline is now in future)
        second_tick = process_pending_escalations(db)
        duplicate = [e for e in second_tick if e["incident_id"] == inc_id]
        assert len(duplicate) == 0

# -------------------------------------------------------------
# Test S: Complete Incident State Transitions
# -------------------------------------------------------------
def test_incident_state_transitions():
    with SessionLocal() as db:
        inc_id = "INC-LIFECYCLE-TEST"
        now_iso = datetime.now(timezone.utc).isoformat()
        inc = Incident(
            id=inc_id,
            asset_id="ASSET-W4-DRAIN08",
            job_id="job-life-01",
            severity="MEDIUM",
            status="DETECTED",
            created_at=now_iso,
            updated_at=now_iso
        )
        db.merge(inc)
        db.commit()

    # DETECTED -> ACKNOWLEDGED via API
    r1 = client.post(f"/api/incidents/{inc_id}/acknowledge", json={"actor": "District Dispatcher", "notes": "Ticket opened"})
    assert r1.status_code == 200
    assert r1.json()["status"] == "ACKNOWLEDGED"

    # ACKNOWLEDGED -> ACTION_IN_PROGRESS
    r2 = client.post(f"/api/incidents/{inc_id}/action", json={"notes": "Crew dispatched with high-pressure jetting truck"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "ACTION_IN_PROGRESS"

    # ACTION_IN_PROGRESS -> RESOLVED
    r3 = client.post(f"/api/incidents/{inc_id}/resolve", json={"notes": "Catchbasin grate cleared of debris. Water draining normally."})
    assert r3.status_code == 200
    assert r3.json()["status"] == "RESOLVED"

    # Verify audit trail contains all stages
    r_detail = client.get(f"/api/incidents/{inc_id}")
    assert r_detail.status_code == 200
    trail = r_detail.json()["audit_trail"]
    actions = [t["action"] for t in trail]
    assert "ACKNOWLEDGED" in actions
    assert "ACTION_IN_PROGRESS" in actions
    assert "RESOLVED" in actions

# -------------------------------------------------------------
# Test U & V: Local Mode without AWS & AWS Status Reporting
# -------------------------------------------------------------
def test_aws_status_reporting():
    status = aws_service.get_status()
    assert "mode" in status
    assert "s3" in status
    assert "ses" in status
    assert "cloudwatch" in status
    assert "iam_policy_recommended" in status
    # In local testing without credentials, must cleanly operate in local mode
    if not os.getenv("AWS_ACCESS_KEY_ID"):
        assert status["mode"] == "LOCAL"
        assert status["aws_connected"] is False

# -------------------------------------------------------------
# Test W: Dashboard API Integration Endpoints
# -------------------------------------------------------------
def test_dashboard_api_endpoints():
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert "text/html" in r_root.headers.get("content-type", "")

    r_dash = client.get("/dashboard")
    assert r_dash.status_code == 200
    assert "text/html" in r_dash.headers.get("content-type", "")

    # SPA client-side route fallback returns index.html
    r_spa = client.get("/incidents/view/any-subroute")
    assert r_spa.status_code == 200
    assert "text/html" in r_spa.headers.get("content-type", "")

    # API 404 must NEVER return index.html
    r_api_404 = client.get("/api/nonexistent_test_route")
    assert r_api_404.status_code == 404
    assert "text/html" not in r_api_404.headers.get("content-type", "")

    assert client.get("/portal").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/api/jobs").status_code == 200
    assert client.get("/api/incidents").status_code == 200
    assert client.get("/api/assets").status_code == 200
    assert client.get("/api/authorities").status_code == 200
    assert client.get("/api/notifications").status_code == 200
    assert client.get("/api/escalation/status").status_code == 200
    assert client.get("/api/metrics").status_code == 200
    assert client.get("/api/benchmark/results").status_code == 200

# -------------------------------------------------------------
# Test Reproducible Benchmark Execution
# -------------------------------------------------------------
def test_opencv_benchmark_execution():
    res = run_opencv_benchmark(frame_count=10, resolution=(320, 240))
    assert res["status"] == "BASELINE_BENCHMARK_COMPLETE"
    assert res["frames_tested"] == 10
    assert res["mean_latency_ms"] > 0
    assert res["throughput_fps"] > 0
    assert res["opencv_version"] != ""
    assert res["cool_status"] in ("AVAILABLE", "NOT_RUN")

# -------------------------------------------------------------
# Test Real-Time WebSocket Channel
# -------------------------------------------------------------
def test_websocket_connection():
    with client.websocket_connect("/ws") as ws:
        ws.send_text("ping")
        data = ws.receive_text()
        assert data == "pong"

# -------------------------------------------------------------
# Test Safe Image Buffer Decoding & RGBA Handling
# -------------------------------------------------------------
def test_safe_image_decoding_and_rgba(tmp_path):
    # 1. RGBA (4-channel) image
    rgba = np.zeros((100, 100, 4), dtype=np.uint8)
    rgba[:, :, :3] = (50, 100, 150)
    rgba[:, :, 3] = 255  # Full alpha
    ok, rgba_bytes = cv2.imencode(".png", rgba)
    assert ok

    # Decode from bytes buffer
    decoded = decode_image_buffer(rgba_bytes.tobytes())
    assert decoded is not None
    assert decoded.shape == (100, 100, 3)  # Converted to BGR 3-channel

    # 2. Decode from Path
    rgba_file = tmp_path / "one.png"
    rgba_file.write_bytes(rgba_bytes.tobytes())
    decoded_file = decode_image_buffer(rgba_file)
    assert decoded_file is not None
    assert decoded_file.shape == (100, 100, 3)

    # 3. Process image media end-to-end
    ev_dir = tmp_path / "evidence_safe"
    ev_dir.mkdir(exist_ok=True)
    metrics, evidence = process_image_media(rgba_file, ev_dir, "job_rgba_test")
    assert len(evidence) == 1
    assert (ev_dir / evidence[0]).is_file()

    # 4. Empty buffer raises ValueError with clear diagnostic
    with pytest.raises(ValueError, match="0 bytes"):
        decode_image_buffer(b"")

    # 5. Corrupted buffer raises ValueError
    with pytest.raises(ValueError, match="corrupt or unsupported"):
        decode_image_buffer(b"\x89PNG\r\n\x1a\ncorrupt_data_payload")

    # 6. Test both /api/uploads and /api/upload alias with real PNG
    r1 = client.post("/api/uploads", files={"file": ("one.png", rgba_bytes.tobytes(), "image/png")})
    assert r1.status_code == 202
    r2 = client.post("/api/upload", files={"file": ("two.png", rgba_bytes.tobytes(), "image/png")})
    assert r2.status_code == 202

# -------------------------------------------------------------
# Test Jobs Pipeline Cleanup, Retry, and Deletion
# -------------------------------------------------------------
def test_job_retry_delete_and_clear_failed(tmp_path):
    # 1. Create a job directly in database with status FAILED
    with SessionLocal() as db:
        test_img = tmp_path / "retry_test.png"
        test_img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake-png-content")
        failed_job = Job(
            id="job_failed_test_99",
            filename="retry_test.png",
            media_type="image",
            status="FAILED",
            progress=100,
            error="OpenCV could not decode image",
            file_path=str(test_img)
        )
        db.add(failed_job)
        db.commit()

    # 2. Test GET /api/jobs?status=FAILED
    r = client.get("/api/jobs?status=FAILED")
    assert r.status_code == 200
    failed_list = r.json()
    assert any(j["job_id"] == "job_failed_test_99" for j in failed_list)

    # 3. Test POST /api/jobs/{id}/retry
    r_retry = client.post("/api/jobs/job_failed_test_99/retry")
    assert r_retry.status_code == 200
    assert r_retry.json()["status"] == "QUEUED"

    # 4. Test DELETE /api/jobs/{id}
    r_del = client.delete("/api/jobs/job_failed_test_99")
    assert r_del.status_code == 200
    assert r_del.json()["success"] is True

    # 5. Test DELETE /api/jobs/failed (clear all failed jobs)
    with SessionLocal() as db:
        db.add(Job(id="job_f1", filename="f1.jpg", media_type="image", status="FAILED", progress=100, file_path="none"))
        db.add(Job(id="job_f2", filename="f2.jpg", media_type="image", status="FAILED", progress=100, file_path="none"))
        db.commit()

    r_clear = client.delete("/api/jobs/failed")
    assert r_clear.status_code == 200
    assert r_clear.json()["deleted_count"] >= 2

    # Verify no FAILED jobs remain
    r_check = client.get("/api/jobs?status=FAILED")
    assert len(r_check.json()) == 0

