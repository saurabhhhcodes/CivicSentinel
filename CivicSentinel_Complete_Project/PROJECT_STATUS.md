# CivicSentinel Project Status & Checkpoint

## 1. Current Architecture
- **Backend**: FastAPI with SQLite (`civicsentinel.db`), SQLAlchemy 2.0 ORM, lifespan background worker for automated incident escalation every 30s.
- **Vision Engine**: OpenCV 4.13.0 headless pipeline featuring safe buffer decoding (`np.frombuffer` + `cv2.imdecode`), RGBA channel normalization to BGR, HSV water color segmentation, adaptive morphological filtering, contour extraction, obstruction index estimation, Laplacian visual clarity evaluation, and annotated evidence generation with bounding boxes.
- **Data Models**: Additive relational schema (`Job`, `Asset`, `Alert`, `Incident`, `AuthorityConfig`, `NotificationAudit`, `AuditLog`).
- **Active Perception & Agent**: Deterministic, auditable decision state machine (`AgenticInvestigationPipeline`) orchestrating frame comparisons, water ratio estimation, obstruction assessment, asset/authority resolution, incident synthesis, and notification dispatch.
- **Risk Engine**: Multi-factor temporal risk assessment (LOW, MEDIUM, HIGH, CRITICAL, UNKNOWN) integrating water ratio proxies, accumulation rates, obstruction indicators, visual confidence, and degraded quality safeguards.
- **Location & Authority Intelligence**: Hierarchical asset registry (GPS coordinates, ward, department, jurisdiction) mapping to multi-level authorities (Level 1 field crew, Level 2 supervisor, Level 3 control room) with Haversine spatial proximity matching.
- **Incident & Notification Lifecycle**: Idempotent dispatch supporting SES, SMTP, and mock local simulation. Cryptographically signed single-use acknowledgement tokens (`token_urlsafe(32)`), deadline tracking, and automatic level-by-level escalation with restart recovery.
- **Frontend OS**: Tactical dark navy (`#0b132b` / `#1c2541`) interface with electric-cyan accent borders (`#00f0ff`), monospaced tactical typography, and 9 operational tabs: `OVERVIEW`, `LIVE STREAM`, `MEDIA`, `TWIN`, `ALERTS`, `TRACE`, `EVAL`, `COOL/AWS`, `SETTINGS`.
- **Jobs Pipeline Controls**: Instant failure purge (`DELETE /api/jobs/failed`), single-job retry (`POST /api/jobs/{id}/retry`), dismissal (`DELETE /api/jobs/{id}`), and sidebar filter pills (`ALL`, `ACTIVE`, `FAILED`).
- **AWS & Performance**: AWS adapter reporting verified connectivity for S3, SES, and CloudWatch without requiring credentials in local mode. Reproducible OpenCV benchmark measuring mean/P95 latency, throughput (FPS), and COOL/Graviton readiness.

## 2. Completed Features
- [x] Initialized Git repository and verified clean baseline.
- [x] Implemented additive database schema for Incidents, Authorities, Notification Audit, and Logs.
- [x] Implemented OpenCV vision pipeline (`vision.py`) with safe buffer decoding, evidence generation, quality assessment, and obstruction detection.
- [x] Implemented multi-factor temporal risk evaluation (`risk_engine.py`) with UNKNOWN fallback for degraded inputs.
- [x] Implemented geographic asset and multi-tier authority resolution (`location_service.py`).
- [x] Implemented email notification dispatch (`notification_service.py`) supporting SES, SMTP, and local simulation with secure tokens.
- [x] Implemented automated escalation engine (`escalation_service.py`) with persistent deadlines, idempotent token acknowledgements, and restart recovery.
- [x] Implemented FastAPI lifespan background worker for automated escalation ticks.
- [x] Implemented AWS service adapter (`aws_service.py`) and OpenCV benchmark service (`benchmark_service.py`).
- [x] Integrated tactical command center in React 18 + TypeScript (`App.tsx`, `style.css`), compiled cleanly (`tsc -b && vite build`) into `dist/`.
- [x] Added job pipeline purge, retry, and dismissal endpoints and UI controls.
- [x] Added comprehensive automated test suite (`tests/test_civicsentinel_core.py` and `tests/test_basic.py`) with 19/19 tests passing.
- [x] Single-port unified serving configured: root `GET /` and `GET /dashboard` serve the pre-built tactical UI from FastAPI on port 8000.

## 3. Key Endpoints
- `GET /`: Serves complete unified tactical UI.
- `GET /health`: OpenCV version, active v5 flag, processing mode.
- `GET /ready`: Database and storage health status.
- `POST /api/uploads` and `POST /api/upload`: Image and video ingestion into OpenCV pipeline.
- `GET /api/jobs`: List jobs (supports `?status=FAILED|COMPLETED`).
- `DELETE /api/jobs/failed`: Purges all failed jobs.
- `POST /api/jobs/{id}/retry`: Re-queues a failed or existing job for OpenCV re-processing.
- `DELETE /api/jobs/{id}`: Dismisses an individual job.
- `GET /api/incidents`: Query incident list with severity/status filters.
- `POST /api/incidents/{id}/acknowledge`: Halts escalation with single-use cryptographic token.
- `POST /api/escalation/process`: Triggers escalation evaluator manually.
- `GET /api/assets`: Registered municipal drainage assets and GPS coordinates.
- `GET /api/authorities`: Ward-to-authority multi-tier escalation hierarchy.
- `POST /api/benchmark/run`: OpenCV performance and throughput benchmark.
- `WS /ws`: Real-time WebSocket event broadcaster.

## 4. Tests and Actual Results
- `.venv\Scripts\python -m pytest -v`: **19 passed in 3.37s** (100% pass rate).
  - `tests/test_basic.py`: 5 passed.
  - `tests/test_civicsentinel_core.py`: 14 passed (safe buffer decoding, RGBA handling, corrupt uploads, jobs retry/clear, temporal risk categories, location/authority resolution, haversine calculation, notification dispatch & token acknowledgment, escalation flow, state transitions, AWS status, dashboard APIs, and OpenCV benchmark execution).
- `frontend`: `npm run build` completed successfully (`tsc -b && vite build`) with 0 errors in 2.23s.
- **FastAPI Static Mount**: Mounted `frontend/dist/assets` at `/assets` and `/dashboard` serving the compiled React 18 SPA directly.
- **WebSocket Channel**: Active at `ws://127.0.0.1:8000/ws` with broadcast hooks for jobs, alerts, and escalations.

## 5. Known Limitations & Unverified Features
- **OpenCV 5 COOL Hardware Acceleration**: Runtime actively uses OpenCV 4.13.0 headless. OpenCV 5 COOL is architecturally validated via `cool_benchmark/baseline.py` but requires compiling against an official OpenCV 5 ARM64 wheel on AWS Graviton3 (`c7g.xlarge`) to produce actual hardware acceleration numbers.
- **Hardware RTSP Cameras**: Live camera tab currently supports browser webcams (`navigator.mediaDevices.getUserMedia`) and tactical simulated multi-camera feeds (`CAM-01` through `CAM-04`). Connecting physical IP/RTSP cameras requires specifying hardware RTSP stream URLs in an ongoing pipeline.
- **Physical Actuation**: System operates strictly as human-in-the-loop decision support; physical floodgates and pumps are never actuated automatically.
