import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.app.main import app
from backend.app.models import SessionLocal, Camera, Incident, NotificationAudit, AuthorityConfig, mask_stream_url
from backend.app.location_service import resolve_camera_and_authority

client = TestClient(app)

def test_camera_stream_url_credential_masking():
    url_with_pass = "rtsp://operator:SecretP@ssword123@192.168.1.100:554/live/ch0"
    masked = mask_stream_url(url_with_pass)
    assert "SecretP@ssword123" not in masked
    assert "rtsp://operator:***@192.168.1.100:554/live/ch0" == masked

    clean_url = "http://192.168.1.50/stream.mjpg"
    assert mask_stream_url(clean_url) == clean_url

def test_camera_registration_and_listing():
    # 1. Register a new road-side camera
    cam_payload = {
        "id": "CAM-TEST-REG-01",
        "name": "High Street Storm Sump Camera",
        "camera_type": "CCTV",
        "stream_url": "rtsp://cctv-admin:SuperSecretKey@10.0.0.45:554/feed",
        "latitude": 12.9720,
        "longitude": 77.5950,
        "road_landmark": "High Street Junction & 2nd Ave",
        "ward": "Ward 4",
        "zone": "Central Zone",
        "city": "Metro City",
        "district": "Central District",
        "assigned_department": "Municipal Stormwater & Flood Control"
    }
    r = client.post("/api/cameras", json=cam_payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "SAVED"
    assert data["location_verification_status"] == "VERIFIED"

    # 2. Get cameras list and verify credentials are NOT exposed
    r_list = client.get("/api/cameras")
    assert r_list.status_code == 200
    cams = r_list.json()
    test_cam = next((c for c in cams if c["id"] == "CAM-TEST-REG-01"), None)
    assert test_cam is not None
    assert "SuperSecretKey" not in test_cam["stream_url"]
    assert "***" in test_cam["stream_url"]

    # 3. Get single camera dossier
    r_single = client.get("/api/cameras/CAM-TEST-REG-01")
    assert r_single.status_code == 200
    assert r_single.json()["ward"] == "Ward 4"
    assert "SuperSecretKey" not in r_single.json()["stream_url"]

def test_location_priority_hierarchy_no_personal_location():
    with SessionLocal() as db:
        # Priority 1: Direct telemetry GPS coordinates override camera default
        res1 = resolve_camera_and_authority(db, camera_id="CAM-01", lat=12.9620, lon=77.6100)
        assert res1["latitude"] == 12.9620
        assert res1["longitude"] == 77.6100

        # Priority 2: Registered camera coordinates used when no direct telemetry lat/lon
        res2 = resolve_camera_and_authority(db, camera_id="CAM-01", lat=None, lon=None)
        assert res2["latitude"] == 12.9716
        assert res2["longitude"] == 77.5946
        assert res2["location_verification_status"] == "VERIFIED"
        assert res2["authority"]["ward"] == "Ward 4"

        # Missing / Unverified location marks incident LOCATION_UNVERIFIED and UNASSIGNED
        res_unverified = resolve_camera_and_authority(db, camera_id="CAM-UNVERIFIED-01")
        assert res_unverified["location_verification_status"] == "LOCATION_UNVERIFIED"
        assert res_unverified["authority"]["assigned_status"] == "UNASSIGNED"
        assert res_unverified["authority"]["level_1_email"] == ""

def test_camera_connectivity_test():
    # Test local/simulated camera
    r_test = client.post("/api/cameras/CAM-01/test")
    assert r_test.status_code == 200
    res = r_test.json()
    assert "connected" in res
    assert res["status"] in ("ONLINE", "DEGRADED", "OFFLINE")

def test_camera_live_sample_and_opencv_analysis():
    # Sample a registered camera and verify genuine OpenCV processing and evidence generation
    r = client.post("/api/cameras/CAM-01/sample")
    assert r.status_code == 200
    res = r.json()
    assert res["camera_id"] == "CAM-01"
    assert "metrics" in res
    assert "water_area_ratio_proxy" in res["metrics"]
    assert "visual_confidence" in res["metrics"]
    assert "risk" in res
    assert res["location"]["ward"] == "Ward 4"

def test_unverified_location_prevents_automatic_dispatch():
    # When an unverified camera samples an elevated hazard, it must NOT automatically dispatch email to random authorities
    r = client.post("/api/cameras/CAM-UNVERIFIED-01/sample")
    assert r.status_code == 200
    res = r.json()
    inc_id = res.get("incident_id")
    if inc_id:
        r_inc = client.get(f"/api/incidents/{inc_id}")
        assert r_inc.status_code == 200
        inc_data = r_inc.json()
        assert inc_data["location_verification_status"] == "LOCATION_UNVERIFIED"
        assert inc_data["status"] == "UNDER_REVIEW"
        assert inc_data["assigned_contact_email"] is None

def test_manual_email_dispatch_and_preview():
    # Create or fetch an incident
    r_inc = client.get("/api/incidents")
    incidents = r_inc.json()
    assert len(incidents) > 0
    target_inc = incidents[0]

    # 1. Test preview
    r_prev = client.post("/api/notifications/preview", json={
        "incident_id": target_inc["id"],
        "custom_subject": "Custom Operator Notice: Drainage Hazard",
        "custom_message": "Immediate silt clearance advised."
    })
    assert r_prev.status_code == 200
    prev_data = r_prev.json()
    assert "Custom Operator Notice" in prev_data["subject"]
    assert "Immediate silt clearance advised." in prev_data["text_body"]
    assert prev_data["is_mock"] is True

    # 2. Test manual dispatch requires confirmed=True
    r_unconfirmed = client.post("/api/notifications/manual-send", json={
        "incident_id": target_inc["id"],
        "recipient_email": "ward4-crew@city-civicsentinel.local",
        "subject": "Manual Dispatch Test",
        "message": "Field inspection mandated.",
        "confirmed": False
    })
    assert r_unconfirmed.status_code == 400

    # 3. Test confirmed manual dispatch in MOCK mode
    r_send = client.post("/api/notifications/manual-send", json={
        "incident_id": target_inc["id"],
        "recipient_email": "ward4-crew@city-civicsentinel.local",
        "subject": "Manual Dispatch Confirmed Test",
        "message": "Field inspection confirmed by operator.",
        "actor": "Senior Engineer Test",
        "confirmed": True,
        "evidence_references": ["evidence_1.jpg"]
    })
    assert r_send.status_code == 200
    send_data = r_send.json()
    assert send_data["success"] is True
    assert send_data["status"] == "SIMULATED"
    assert send_data["is_mock"] is True

    # Verify incident audit trail updated with manual dispatch
    r_updated = client.get(f"/api/incidents/{target_inc['id']}")
    assert r_updated.status_code == 200
    trail = r_updated.json()["audit_trail"]
    assert any(t.get("action") == "MANUAL_EMAIL_DISPATCH" for t in trail)
