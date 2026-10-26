# CivicSentinel — Agentic Visual Infrastructure Intelligence & Incident Response Platform

> **OpenCV AI Competition 2026, Powered by AWS**  
> *Autonomous stormwater drainage surveillance, multi-factor temporal risk assessment, authoritative incident dispatch, and multi-tier escalation.*

---

## 1. System Overview

CivicSentinel transforms passive infrastructure cameras and inspection uploads into an active, decision-support operations platform. The system operates on a verified perception-decision-action loop:

```
VISUAL OBSERVATION (Image / Video / Live Camera Snapshot)
    ↳ OPENCV VISION PIPELINE (HSV segmentation, morphology, obstruction detection, Laplacian clarity)
    ↳ ACTIVE PERCEPTION AGENT (Decision state machine, ROI & frame comparison, digital twin update)
    ↳ TEMPORAL RISK ENGINE (Hysteresis, multi-factor scoring, UNKNOWN fallback safeguard)
    ↳ LOCATION & JURISDICTION RESOLUTION (Haversine spatial mapping, ward hierarchy)
    ↳ INCIDENT LIFECYCLE MANAGEMENT (Idempotent state machine, audit logs)
    ↳ AUTHORITY NOTIFICATION (SES / SMTP / Mock dispatch, cryptographically secured tokens)
    ↳ AUTOMATED MULTI-TIER ESCALATION (FastAPI lifespan background worker, restart recovery)
    ↳ OPERATIONAL DASHBOARD (Real-time incident response, evidence viewer, benchmark suite)
```

---

## 2. Quick Start (Windows PowerShell / CMD)

### Recommended 1-Click Startup
In Windows PowerShell from the project root:
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\start.ps1
```
Or double-click `start.bat` in File Explorer.

`start.ps1` automatically:
1. Verifies/creates Python virtual environment (`.venv`) and installs backend requirements.
2. Verifies `.env` from `.env.example`.
3. Checks/builds the React 18 single-page application into `frontend/dist`.
4. Starts the FastAPI backend with lifespan escalation worker on `http://127.0.0.1:8000`.

To stop the platform:
```cmd
stop.bat
```
Or in PowerShell:
```powershell
.\stop.ps1
```

---

## 3. Localhost Endpoints

| Resource | URL | Description |
|---|---|---|
| **Integrated Dashboard** | [http://127.0.0.1:8000/](http://127.0.0.1:8000/) | React 18 Tactical SPA served directly from FastAPI (Single-Port mode). Also accessible at `/dashboard`. |
| **Interactive OpenAPI (Swagger)** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Interactive endpoint tester and schema viewer. |
| **ReDoc Documentation** | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) | Formal API documentation specification. |
| **Health Diagnostics** | [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) | Real runtime version verification (`opencv_version`, `opencv5_active`). |
| **Real-Time WebSocket** | `ws://127.0.0.1:8000/ws` | Bi-directional event stream for live job, camera, and incident updates. |
| **Vite Dev Server (Optional)** | [http://localhost:5173/](http://localhost:5173/) | Dual-server mode with hot module replacement (`cd frontend && npm run dev`). |

---

## 4. Key Capabilities Implemented

### A. Substantive OpenCV Vision Pipeline (`backend/app/vision.py`)
- **Format Validation**: Header magic-byte inspection rejecting disguised executables and corrupt payloads (`JPEG`, `PNG`, `WebP`, `BMP`, `MP4`, `AVI`, `MOV`, `MKV`, `WEBM`).
- **Image Quality & Clarity**: Evaluates Laplacian variance to detect blurred or degraded inputs. Low-quality imagery transitions risk to `UNKNOWN` rather than falsely declaring safety.
- **Morphological Analysis**: HSV-space candidate water segmentation with adaptive opening/closing structuring elements.
- **Obstruction Indexing**: Edge-density and high-frequency structural filtering to detect debris accumulation and culvert grating blockages.
- **Annotated Evidence Generation**: Renders visual evidence images with cyan bounding contours and orange attention bounding boxes.

### B. Registered Road-Side Cameras & Live OpenCV Analysis (`backend/app/models.py`, `backend/app/main.py`)
- CCTV and IP camera registration with stream types (RTSP, IP_CAMERA, ONVIF, MOCK_TEST), GPS coordinates, and administrative ward mapping.
- **Credential Protection**: Passwords, RTSP credentials, and tokens are sanitized via regex (`mask_stream_url`) before ever being returned in API responses, logs, or exports.
- **Live Stream Testing & Sampling**: Genuine OpenCV processing of sampled camera frames with explainable risk assessment and connection diagnostics.

### C. Removed Personal-Location Dependency (`backend/app/location_service.py`)
- Strict 4-level camera priority hierarchy: (1) Camera GPS, (2) Administrator coordinates, (3) Registered asset location, (4) Road/ward/zone.
- Unverified camera coordinates trigger `LOCATION_UNVERIFIED` and suspend automated municipal email alerts until administrator verification.

### D. Operational Email Inbox & Manual Dispatch (`frontend/src/App.tsx`, `backend/app/notification_service.py`)
- Dedicated `EMAILS` operational inbox with status filtering (`NEW`, `READY_TO_SEND`, `SENT`, `ACKNOWLEDGED`, `OVERDUE`, `ESCALATED`, `RESOLVED`, `DELIVERY_FAILED`).
- Manual email dispatch workflow with location review, editable subject/body, HTML email preview modal, and explicit operator sign-off checkbox.

### E. Incident Response & Multi-Tier Escalation (`backend/app/escalation_service.py`)
- **Hierarchical Jurisdictions**: Assets map to administrative wards with Level 1 (Field Crew), Level 2 (Ward Supervisor), and Level 3 (Municipal Control Room).
- **Automated Escalation Worker**: FastAPI lifespan task runs an evaluation loop every 30s. Overdue deadlines trigger level promotion automatically.
- **Restart Recovery**: Overdue deadlines persist in SQLite and are evaluated immediately on server startup.
- **Secure Acknowledgement**: Cryptographically random single-use tokens (`secrets.token_urlsafe(32)`) allow field officers to acknowledge incidents via email link or dashboard button, halting the escalation timer.

### F. Multi-Provider Notifications (`backend/app/notification_service.py`)
- Supports **Amazon SES** (cloud), **SMTP** (staging/testing), and **MOCK** (local zero-dependency simulation).
- Complete notification audit entries stored in SQLite (`NotificationAudit`).

### G. AWS Status & Reproducible OpenCV Benchmark
- `aws_service.py` reports connectivity for S3, SES, and CloudWatch without requiring AWS credentials in local mode.
- `benchmark_service.py` executes timed runs measuring mean latency, P95 latency, and throughput (FPS) across warm-up and repeated cycles.

---

## 5. Automated Testing

Run the full test suite with:
```powershell
.\.venv\Scripts\python -m pytest -v
```

**Results (26/26 Passed, 100%):**
- `tests/test_basic.py`: Health, readiness, extension validation, proxy bounds, independent job execution (5 passed).
- `tests/test_camera_email_additive.py`: Credential masking, camera registration, priority hierarchy without personal location, connectivity test, OpenCV sampling, unverified location safety guard, manual dispatch with preview (7 passed).
- `tests/test_civicsentinel_core.py`: Image/video processing, corrupt file rejection, temporal risk categories, location/authority resolution, Haversine spatial math, notification dispatch & secure token acknowledgement, escalation flow, state transitions, AWS status, dashboard API endpoints, benchmark execution, WebSocket ping-pong, safe image buffer decoding / RGBA normalization, and jobs pipeline retry/clear/delete (14 passed).

---

## 6. Docker Deployment (Local Development)

```bash
docker compose up --build
```
Access the application on `http://localhost:8000`.

---

## 7. Operational Limitations & Responsible Safety Policy

1. **Safety Constraints**: CivicSentinel strictly acts as a decision-support platform. It does not automatically actuate physical flood gates, pumps, or sluices without human authorization.
2. **Vision Proxy Calibration**: Computed water ratios are 2D visual surface proxies. Calibrated depth readings require physical staff gauges or LiDAR sensors at monitored culverts.
3. **OpenCV Version Reporting**: The environment runs OpenCV 4.13.0 headless. The platform transparently reports `opencv5_active: false` to ensure accuracy for the competition evaluation.
4. **AWS Status**: When AWS credentials are not configured, the platform runs in full local mode (`LOCAL / MOCK`), preserving full functionality with zero cloud charges.
