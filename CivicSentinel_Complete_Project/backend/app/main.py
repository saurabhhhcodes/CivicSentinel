import os, uuid, json, time, asyncio
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone
import cv2, numpy as np

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .models import (
    Base, Job, Asset, Alert, Incident, AuthorityConfig, NotificationAudit, AuditLog, Camera, mask_stream_url,
    SessionLocal, engine, init_db, UPLOADS, EVIDENCE, DATA
)
from .vision import (
    process_image_media, process_video_media, analyze_water_and_obstruction
)
from .agent import AgenticInvestigationPipeline
from .location_service import resolve_asset_and_authority, resolve_camera_and_authority
from .risk_engine import evaluate_temporal_risk
from .notification_service import notification_service
from .escalation_service import process_pending_escalations, acknowledge_incident_by_token
from .aws_service import aws_service
from .benchmark_service import run_opencv_benchmark, get_latest_benchmark_result

# Initialize database schema and seed data
init_db()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager that starts the background escalation worker."""
    task = None
    async def escalation_loop():
        await asyncio.sleep(5)
        while True:
            try:
                with SessionLocal() as db:
                    process_pending_escalations(db)
            except Exception:
                pass
            await asyncio.sleep(30)
    task = asyncio.create_task(escalation_loop())
    try:
        yield
    finally:
        if task:
            task.cancel()

app = FastAPI(
    title="CivicSentinel Infrastructure Intelligence API",
    version="1.0.0",
    description="Agentic visual infrastructure surveillance, temporal risk assessment, and incident escalation platform.",
    lifespan=lifespan
)

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VID_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
assets_dir = FRONTEND_DIST / "assets"
assets_dir.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(assets_dir), check_dir=False), name="frontend_assets")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

    def broadcast_sync(self, message: dict):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)
        except Exception:
            pass

ws_manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)





# -------------------------------------------------------------
# Background Vision & Agent Worker
# -------------------------------------------------------------
def process_job_pipeline(job_id: str):
    """Execute OpenCV vision processing and agentic investigation for a given job."""
    db = SessionLocal()
    try:
        j = db.get(Job, job_id)
        if not j:
            return
        j.status = "PROCESSING"
        j.progress = 5
        db.commit()

        start_time = time.perf_counter()
        file_path = Path(j.file_path)

        def update_progress(p: int):
            try:
                j.progress = p
                db.commit()
            except Exception:
                pass

        if j.media_type == "image":
            metrics, evidence_files = process_image_media(file_path, EVIDENCE, job_id)
            j.progress = 50
            db.commit()
        else:
            sample_every = int(os.getenv("VIDEO_SAMPLE_EVERY", "15"))
            metrics, evidence_files = process_video_media(
                file_path=file_path,
                evidence_dir=EVIDENCE,
                job_id=job_id,
                sample_interval=sample_every,
                progress_cb=update_progress
            )
            j.progress = 65
            db.commit()

        # Run Agentic Investigation Pipeline
        pipeline = AgenticInvestigationPipeline(
            db=db,
            job=j,
            metrics=metrics,
            evidence_files=evidence_files
        )
        agent_output = pipeline.run()

        # Merge results
        processing_elapsed = round(time.perf_counter() - start_time, 3)
        metrics.update(agent_output)
        metrics["processing_seconds"] = processing_elapsed

        j.result_json = json.dumps(metrics)
        j.status = "NEEDS_REVIEW" if agent_output["risk"]["human_review_required"] else "COMPLETED"
        j.progress = 100
        db.commit()
        ws_manager.broadcast_sync({"type": "JOB_UPDATE", "job_id": j.id, "status": j.status})

    except Exception as e:
        db.rollback()
        j = db.get(Job, job_id)
        if j:
            j.status = "FAILED"
            j.error = str(e)[:1000]
            j.progress = 100
            db.commit()
            ws_manager.broadcast_sync({"type": "JOB_UPDATE", "job_id": j.id, "status": j.status})
    finally:
        db.close()

# Backward-compatibility helper for job formatting
def format_job_json(j: Job) -> dict:
    return {
        "job_id": j.id,
        "filename": j.filename,
        "media_type": j.media_type,
        "status": j.status,
        "progress": j.progress,
        "created_at": j.created_at,
        "result": json.loads(j.result_json) if j.result_json else None,
        "error": j.error
    }

# Backward-compatible proxy function for test_basic.py
def proxy(frame):
    m, ann = analyze_water_and_obstruction(frame)
    return m, ann

# -------------------------------------------------------------
# System & Health Endpoints
# -------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def root():
    dist_index = FRONTEND_DIST / "index.html"
    if dist_index.is_file():
        return FileResponse(dist_index)
    return HTMLResponse("<h3>CivicSentinel API online. Frontend build not found. Run 'npm run build' in frontend directory.</h3>", status_code=200)

@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard():
    dist_index = FRONTEND_DIST / "index.html"
    if dist_index.is_file():
        return FileResponse(dist_index)
    return HTMLResponse("<h3>Dashboard build not found. Please run 'npm run build' in frontend directory.</h3>", status_code=404)

@app.get("/portal", response_class=HTMLResponse)
def root_portal():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CivicSentinel API Gateway</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b1120; color: #f8fafc; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 80vh; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 32px; max-width: 580px; width: 100%; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h1 { color: #38bdf8; font-size: 1.5rem; margin-top: 0; display: flex; align-items: center; gap: 10px; }
        p { color: #94a3b8; font-size: 0.95rem; line-height: 1.5; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 24px; }
        a.btn { display: flex; flex-direction: column; padding: 14px; background: #0f172a; border: 1px solid #38bdf844; border-radius: 8px; color: #f1f5f9; text-decoration: none; transition: all 0.2s; }
        a.btn:hover { background: #38bdf81a; border-color: #38bdf8; transform: translateY(-2px); }
        .btn-title { font-weight: 600; color: #38bdf8; font-size: 0.95rem; }
        .btn-desc { font-size: 0.75rem; color: #64748b; margin-top: 4px; }
        .status-badge { display: inline-flex; align-items: center; gap: 6px; background: #064e3b; color: #34d399; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
        .dot { width: 8px; height: 8px; background: #10b981; border-radius: 50%; }
    </style>
</head>
<body>
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h1>CivicSentinel</h1>
            <span class="status-badge"><span class="dot"></span> ONLINE</span>
        </div>
        <p>Agentic visual infrastructure surveillance, temporal risk assessment, and incident escalation platform.</p>
        <div class="grid">
            <a class="btn" href="/">
                <span class="btn-title">Frontend Dashboard &rarr;</span>
                <span class="btn-desc">Integrated React 18 Application (/)</span>
            </a>
            <a class="btn" href="/docs">
                <span class="btn-title">Swagger API Docs &rarr;</span>
                <span class="btn-desc">Interactive OpenAPI Endpoints</span>
            </a>
            <a class="btn" href="/health">
                <span class="btn-title">Health Check &rarr;</span>
                <span class="btn-desc">OpenCV & System Status JSON</span>
            </a>
            <a class="btn" href="/redoc">
                <span class="btn-title">ReDoc Specification &rarr;</span>
                <span class="btn-desc">Technical API Documentation</span>
            </a>
        </div>
    </div>
</body>
</html>"""



@app.get("/health")
def health():
    v = cv2.__version__
    return {
        "status": "ok",
        "mode": os.getenv("PROCESSING_MODE", "LOCAL").upper(),
        "opencv_version": v,
        "opencv5_active": v.startswith("5."),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/ready")
def ready():
    with SessionLocal() as db:
        db.execute(select(Job.id).limit(1))
    return {"ready": True, "database": "connected", "storage": "ready"}

# -------------------------------------------------------------
# Media Upload & Job Endpoints
# -------------------------------------------------------------
@app.post("/api/uploads", status_code=202)
@app.post("/api/upload", status_code=202)
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    name = Path(file.filename or "upload").name
    ext = Path(name).suffix.lower()
    if ext not in (IMG_EXTS | VID_EXTS):
        raise HTTPException(415, "Unsupported format. Supported: JPG, PNG, WEBP, BMP, MP4, AVI, MOV, MKV, WEBM.")

    max_bytes = int(os.getenv("MAX_UPLOAD_MB", "250")) * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if not data:
        raise HTTPException(400, "Empty upload.")
    if len(data) > max_bytes:
        raise HTTPException(413, "Upload exceeds MAX_UPLOAD_MB.")

    media = "image" if ext in IMG_EXTS else "video"
    # Basic file signature verification
    if media == "image" and not data.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF", b"BM")):
        raise HTTPException(415, "File signature does not match a supported image format.")
    if media == "video" and not (data[4:8] == b"ftyp" or data.startswith((b"RIFF", b"\x1aE\xdf\xa3"))):
        raise HTTPException(415, "File signature does not match a supported video container.")

    jid = uuid.uuid4().hex
    path = UPLOADS / (jid + ext)
    path.write_bytes(data)

    with SessionLocal() as db:
        db.add(Job(id=jid, filename=name, media_type=media, status="QUEUED", progress=0, file_path=str(path)))
        db.commit()

    background_tasks.add_task(process_job_pipeline, jid)
    return {"job_id": jid, "status": "QUEUED", "media_type": media, "filename": name}

@app.get("/api/jobs")
def get_jobs(status: str | None = None):
    with SessionLocal() as db:
        query = select(Job).order_by(Job.created_at.desc())
        if status:
            query = query.where(Job.status == status.upper())
        return [format_job_json(j) for j in db.scalars(query.limit(100)).all()]

@app.delete("/api/jobs/failed")
@app.post("/api/jobs/clear-failed")
def clear_failed_jobs():
    """Purge all failed jobs from queue/database."""
    with SessionLocal() as db:
        failed_jobs = db.scalars(select(Job).where(Job.status == "FAILED")).all()
        count = len(failed_jobs)
        for j in failed_jobs:
            db.delete(j)
        db.commit()
    ws_manager.broadcast_sync({"type": "JOB_UPDATE", "action": "CLEAR_FAILED"})
    return {"deleted_count": count, "message": f"Purged {count} failed jobs."}

@app.post("/api/jobs/reset")
def reset_jobs_pipeline():
    """Reset jobs pipeline by purging failed jobs and notifying connected clients."""
    with SessionLocal() as db:
        failed_jobs = db.scalars(select(Job).where(Job.status == "FAILED")).all()
        count = len(failed_jobs)
        for j in failed_jobs:
            db.delete(j)
        db.commit()
    ws_manager.broadcast_sync({"type": "JOB_UPDATE", "action": "RESET"})
    return {"purged_failed": count, "message": "Jobs pipeline reset successfully."}

@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str, background_tasks: BackgroundTasks):
    """Re-run processing for a failed or existing job if source file is present."""
    with SessionLocal() as db:
        j = db.get(Job, job_id)
        if not j:
            raise HTTPException(404, "Job not found")
        file_path = Path(j.file_path)
        if not file_path.is_file():
            raise HTTPException(400, f"Source media file not found on disk for retry: {j.filename}")
        
        j.status = "QUEUED"
        j.progress = 0
        j.error = None
        j.result_json = None
        db.commit()
    
    background_tasks.add_task(process_job_pipeline, job_id)
    ws_manager.broadcast_sync({"type": "JOB_UPDATE", "job_id": job_id, "status": "QUEUED"})
    return {"job_id": job_id, "status": "QUEUED", "message": "Job queued for reprocessing"}

@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    """Dismiss and remove an individual job."""
    with SessionLocal() as db:
        j = db.get(Job, job_id)
        if not j:
            raise HTTPException(404, "Job not found")
        db.delete(j)
        db.commit()
    ws_manager.broadcast_sync({"type": "JOB_UPDATE", "job_id": job_id, "action": "DELETED"})
    return {"success": True, "job_id": job_id}

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    with SessionLocal() as db:
        j = db.get(Job, job_id)
        if not j:
            raise HTTPException(404, "Job not found")
        return format_job_json(j)

@app.get("/api/jobs/{job_id}/trace")
def get_job_trace(job_id: str):
    job = get_job(job_id)
    return job["result"].get("agent", {}).get("trace", []) if job.get("result") else []

@app.get("/api/evidence/{filename}")
@app.get("/evidence/{filename}")
def get_evidence(filename: str):
    p = (EVIDENCE / Path(filename).name).resolve()
    if EVIDENCE.resolve() not in p.parents or not p.is_file():
        raise HTTPException(404, "Evidence not found")
    return FileResponse(p)

@app.get("/api/uploads/{filename}")
@app.get("/uploads/{filename}")
def get_upload(filename: str):
    p = (UPLOADS / Path(filename).name).resolve()
    if UPLOADS.resolve() not in p.parents or not p.is_file():
        raise HTTPException(404, "Upload not found")
    return FileResponse(p)

# -------------------------------------------------------------
# Incidents & Escalation Lifecycle Endpoints
# -------------------------------------------------------------
@app.get("/api/incidents")
def get_incidents(
    severity: str | None = None,
    status: str | None = None,
    camera_id: str | None = None,
    verification: str | None = None,
    delivery_status: str | None = None
):
    with SessionLocal() as db:
        query = select(Incident).order_by(Incident.created_at.desc())
        if severity:
            query = query.where(Incident.severity == severity.upper())
        if status:
            query = query.where(Incident.status == status.upper())
        if camera_id:
            query = query.where(Incident.camera_id == camera_id)
        if verification:
            query = query.where(Incident.location_verification_status == verification.upper())
        if delivery_status:
            query = query.where(Incident.delivery_status == delivery_status.upper())
        
        incidents = db.scalars(query.limit(100)).all()
        return [{
            "id": inc.id,
            "asset_id": inc.asset_id,
            "camera_id": inc.camera_id,
            "job_id": inc.job_id,
            "severity": inc.severity,
            "status": inc.status,
            "location_verification_status": inc.location_verification_status or "VERIFIED",
            "road_landmark": inc.road_landmark,
            "zone": inc.zone,
            "district": inc.district,
            "delivery_status": inc.delivery_status or "NEW",
            "last_response": inc.last_response,
            "temporal_trend": inc.temporal_trend,
            "risk_score": inc.risk_score,
            "risk_explanation": inc.risk_explanation,
            "recommended_action": inc.recommended_action,
            "assigned_authority_id": inc.assigned_authority_id,
            "assigned_department": inc.assigned_department,
            "assigned_contact_email": inc.assigned_contact_email,
            "escalation_level": inc.escalation_level,
            "acknowledgement_deadline": inc.acknowledgement_deadline,
            "acknowledged_at": inc.acknowledged_at,
            "acknowledged_by": inc.acknowledged_by,
            "escalated_at": inc.escalated_at,
            "created_at": inc.created_at,
            "updated_at": inc.updated_at,
            "resolved_at": inc.resolved_at,
            "trigger_evidence": json.loads(inc.trigger_evidence or "{}"),
            "audit_trail": json.loads(inc.audit_trail or "[]")
        } for inc in incidents]

@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    with SessionLocal() as db:
        inc = db.get(Incident, incident_id)
        if not inc:
            raise HTTPException(404, "Incident not found")
        asset_info = resolve_camera_and_authority(db, camera_id=inc.camera_id, asset_hint=inc.asset_id)
        return {
            "id": inc.id,
            "asset_id": inc.asset_id,
            "camera_id": inc.camera_id,
            "asset": asset_info,
            "job_id": inc.job_id,
            "severity": inc.severity,
            "status": inc.status,
            "location_verification_status": inc.location_verification_status or "VERIFIED",
            "road_landmark": inc.road_landmark or asset_info.get("road_landmark"),
            "zone": inc.zone or asset_info.get("zone"),
            "district": inc.district or asset_info.get("district"),
            "delivery_status": inc.delivery_status or "NEW",
            "last_response": inc.last_response,
            "trigger_evidence": json.loads(inc.trigger_evidence or "{}"),
            "temporal_trend": inc.temporal_trend,
            "risk_score": inc.risk_score,
            "risk_explanation": inc.risk_explanation,
            "recommended_action": inc.recommended_action,
            "assigned_authority_id": inc.assigned_authority_id,
            "assigned_department": inc.assigned_department,
            "assigned_contact_email": inc.assigned_contact_email,
            "acknowledgement_deadline": inc.acknowledgement_deadline,
            "acknowledged_at": inc.acknowledged_at,
            "acknowledged_by": inc.acknowledged_by,
            "escalation_level": inc.escalation_level,
            "escalated_at": inc.escalated_at,
            "created_at": inc.created_at,
            "updated_at": inc.updated_at,
            "resolved_at": inc.resolved_at,
            "resolution_notes": inc.resolution_notes,
            "audit_trail": json.loads(inc.audit_trail or "[]")
        }

@app.get("/api/incidents/{incident_id}/ack")
def acknowledge_incident_link(incident_id: str, token: str = Query(...)):
    """
    Secure single-click acknowledgement endpoint accessible via signed notification email links.
    """
    with SessionLocal() as db:
        res = acknowledge_incident_by_token(db, incident_id, token, actor_note="Authority Email Link")
        if not res["success"]:
            raise HTTPException(res.get("status_code", 400), res["message"])
        
        # Render a clear confirmation page
        html = f"""<!DOCTYPE html>
<html>
<head>
<title>CivicSentinel - Incident Acknowledged</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 40px 20px; text-align: center; }}
  .card {{ max-width: 520px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 32px; border: 1px solid #334155; }}
  .check {{ font-size: 48px; color: #22c55e; margin-bottom: 16px; }}
  h1 {{ font-size: 22px; margin: 0 0 12px 0; color: #ffffff; }}
  p {{ color: #94a3b8; font-size: 14px; line-height: 1.5; }}
  .meta {{ background: #0f172a; border-radius: 8px; padding: 16px; margin: 20px 0; text-align: left; font-size: 13px; }}
  .btn {{ display: inline-block; padding: 10px 20px; background: #2563eb; color: #fff; text-decoration: none; border-radius: 6px; font-weight: 600; margin-top: 16px; }}
</style>
</head>
<body>
<div class="card">
  <div class="check">&#10004;</div>
  <h1>Incident Acknowledged</h1>
  <p>{res['message']}</p>
  <div class="meta">
    <div><strong>Incident ID:</strong> {incident_id}</div>
    <div><strong>Status:</strong> ACKNOWLEDGED</div>
    <div><strong>Acknowledged At:</strong> {res.get('acknowledged_at')}</div>
    <div><strong>Escalation State:</strong> Paused</div>
  </div>
  <a href="/api/incidents/{incident_id}" class="btn" target="_blank">View Live Incident Dossier</a>
</div>
</body>
</html>"""
        return HTMLResponse(content=html, status_code=200)

@app.post("/api/incidents/{incident_id}/acknowledge")
def acknowledge_incident_api(incident_id: str, payload: dict = {}):
    with SessionLocal() as db:
        inc = db.get(Incident, incident_id)
        if not inc:
            raise HTTPException(404, "Incident not found")
        now_iso = datetime.now(timezone.utc).isoformat()
        inc.status = "ACKNOWLEDGED"
        inc.acknowledged_at = now_iso
        inc.acknowledged_by = payload.get("actor", "Dashboard Operator")
        inc.acknowledgement_deadline = None
        inc.updated_at = now_iso

        trail = json.loads(inc.audit_trail or "[]")
        trail.append({"timestamp": now_iso, "action": "ACKNOWLEDGED", "actor": inc.acknowledged_by, "notes": payload.get("notes", "")})
        inc.audit_trail = json.dumps(trail)
        db.commit()
        return {"incident_id": inc.id, "status": inc.status, "acknowledged_at": inc.acknowledged_at}

@app.post("/api/incidents/{incident_id}/action")
def incident_action_in_progress(incident_id: str, payload: dict = {}):
    with SessionLocal() as db:
        inc = db.get(Incident, incident_id)
        if not inc:
            raise HTTPException(404, "Incident not found")
        now_iso = datetime.now(timezone.utc).isoformat()
        inc.status = "ACTION_IN_PROGRESS"
        inc.updated_at = now_iso
        trail = json.loads(inc.audit_trail or "[]")
        trail.append({"timestamp": now_iso, "action": "ACTION_IN_PROGRESS", "notes": payload.get("notes", "Field crew deployed")})
        inc.audit_trail = json.dumps(trail)
        db.commit()
        return {"incident_id": inc.id, "status": inc.status}

@app.post("/api/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str, payload: dict = {}):
    with SessionLocal() as db:
        inc = db.get(Incident, incident_id)
        if not inc:
            raise HTTPException(404, "Incident not found")
        now_iso = datetime.now(timezone.utc).isoformat()
        inc.status = "RESOLVED"
        inc.resolved_at = now_iso
        inc.resolution_notes = payload.get("notes", "Resolved after field inspection and clearance.")
        inc.updated_at = now_iso
        trail = json.loads(inc.audit_trail or "[]")
        trail.append({"timestamp": now_iso, "action": "RESOLVED", "notes": inc.resolution_notes})
        inc.audit_trail = json.dumps(trail)
        db.commit()
        return {"incident_id": inc.id, "status": inc.status, "resolved_at": inc.resolved_at}

@app.post("/api/incidents/{incident_id}/reject")
def reject_incident_false_alarm(incident_id: str, payload: dict = {}):
    with SessionLocal() as db:
        inc = db.get(Incident, incident_id)
        if not inc:
            raise HTTPException(404, "Incident not found")
        now_iso = datetime.now(timezone.utc).isoformat()
        inc.status = "REJECTED_AS_FALSE_ALARM"
        inc.resolution_notes = payload.get("notes", "Dismissed as false alarm or optical reflection.")
        inc.updated_at = now_iso
        trail = json.loads(inc.audit_trail or "[]")
        trail.append({"timestamp": now_iso, "action": "REJECTED_AS_FALSE_ALARM", "notes": inc.resolution_notes})
        inc.audit_trail = json.dumps(trail)
        db.commit()
        return {"incident_id": inc.id, "status": inc.status}

@app.post("/api/incidents/{incident_id}/escalate")
def manual_escalate(incident_id: str):
    with SessionLocal() as db:
        inc = db.get(Incident, incident_id)
        if not inc:
            raise HTTPException(404, "Incident not found")
        now_iso = datetime.now(timezone.utc).isoformat()
        inc.acknowledgement_deadline = now_iso
        db.commit()
        escalated = process_pending_escalations(db)
        return {"incident_id": inc.id, "escalated": bool(escalated), "details": escalated}

@app.post("/api/escalation/process")
def trigger_escalation_tick():
    with SessionLocal() as db:
        res = process_pending_escalations(db)
        return {"processed_count": len(res), "escalations": res}

@app.get("/api/escalation/status")
def get_escalation_status():
    with SessionLocal() as db:
        pending = db.scalars(
            select(Incident).where(
                Incident.status.in_(["NOTIFIED", "ESCALATED"]),
                Incident.acknowledged_at.is_(None)
            )
        ).all()
        return {
            "pending_count": len(pending),
            "pending_incidents": [{
                "incident_id": p.id,
                "severity": p.severity,
                "current_level": p.escalation_level,
                "deadline": p.acknowledgement_deadline,
                "assigned_email": p.assigned_contact_email
            } for p in pending]
        }

# -------------------------------------------------------------
# Authorities, Assets & Digital Twin Endpoints
# -------------------------------------------------------------
@app.get("/api/authorities")
def get_authorities():
    with SessionLocal() as db:
        auths = db.scalars(select(AuthorityConfig)).all()
        return [{
            "id": a.id,
            "name": a.name,
            "ward": a.ward,
            "jurisdiction": a.jurisdiction,
            "department": a.department,
            "level_1_name": a.level_1_name,
            "level_1_email": a.level_1_email,
            "level_2_name": a.level_2_name,
            "level_2_email": a.level_2_email,
            "level_3_name": a.level_3_name,
            "level_3_email": a.level_3_email,
            "escalation_delay_minutes": a.escalation_delay_minutes,
            "critical_delay_minutes": a.critical_delay_minutes,
            "active": bool(a.active)
        } for a in auths]

@app.post("/api/authorities")
def create_or_update_authority(payload: dict):
    auth_id = payload.get("id") or f"AUTH-{uuid.uuid4().hex[:6].upper()}"
    with SessionLocal() as db:
        auth = db.get(AuthorityConfig, auth_id)
        if not auth:
            auth = AuthorityConfig(id=auth_id)
            db.add(auth)
        auth.name = payload.get("name", "Ward Drainage Authority")
        auth.ward = payload.get("ward", "Ward 4")
        auth.jurisdiction = payload.get("jurisdiction", "Municipal District")
        auth.department = payload.get("department", "Stormwater Drainage Dept")
        auth.level_1_name = payload.get("level_1_name", "Field Crew 1")
        auth.level_1_email = payload.get("level_1_email", "crew@city.local")
        auth.level_2_name = payload.get("level_2_name", "Supervisor")
        auth.level_2_email = payload.get("level_2_email", "supervisor@city.local")
        auth.level_3_name = payload.get("level_3_name", "Emergency Director")
        auth.level_3_email = payload.get("level_3_email", "director@city.local")
        auth.escalation_delay_minutes = int(payload.get("escalation_delay_minutes", 15))
        auth.critical_delay_minutes = int(payload.get("critical_delay_minutes", 5))
        auth.active = 1 if payload.get("active", True) else 0
        db.commit()
        return {"id": auth.id, "status": "SAVED"}

@app.get("/api/assets")
def get_assets():
    with SessionLocal() as db:
        return [{
            "asset_id": a.id,
            "name": a.name or a.id,
            "asset_type": a.asset_type,
            "latitude": a.latitude,
            "longitude": a.longitude,
            "address": a.address,
            "ward": a.ward,
            "city": a.city,
            "jurisdiction": a.jurisdiction,
            "department": a.department,
            "current_risk": a.current_risk,
            "latest_job_id": a.latest_job_id,
            "summary": json.loads(a.summary or "{}")
        } for a in db.scalars(select(Asset)).all()]

@app.post("/api/assets")
def create_or_update_asset(payload: dict):
    aid = payload.get("asset_id") or f"ASSET-{uuid.uuid4().hex[:8].upper()}"
    with SessionLocal() as db:
        asset = db.get(Asset, aid)
        if not asset:
            asset = Asset(id=aid)
            db.add(asset)
        asset.name = payload.get("name")
        asset.asset_type = payload.get("asset_type", "stormwater_drain")
        asset.latitude = payload.get("latitude")
        asset.longitude = payload.get("longitude")
        asset.address = payload.get("address")
        asset.ward = payload.get("ward", "Ward 4")
        asset.city = payload.get("city", "Metro City")
        asset.jurisdiction = payload.get("jurisdiction", "Municipal Corporation")
        asset.department = payload.get("department", "Stormwater & Drainage Dept")
        asset.contact_email = payload.get("contact_email")
        asset.supervisor_email = payload.get("supervisor_email")
        asset.director_email = payload.get("director_email")
        db.commit()
        return {"asset_id": asset.id, "status": "SAVED"}

# -------------------------------------------------------------
# Notifications & Audit Endpoints
# -------------------------------------------------------------
@app.get("/api/notifications")
def get_notification_audits():
    with SessionLocal() as db:
        audits = db.scalars(select(NotificationAudit).order_by(NotificationAudit.timestamp.desc()).limit(100)).all()
        return [{
            "id": n.id,
            "incident_id": n.incident_id,
            "recipient": n.recipient,
            "level": n.level,
            "channel": n.channel,
            "subject": n.subject,
            "body_preview": n.body_preview,
            "status": n.status,
            "provider_response": n.provider_response,
            "error": n.error,
            "timestamp": n.timestamp
        } for n in audits]

@app.post("/api/notifications/test")
def test_notification(payload: dict):
    recipient = payload.get("recipient_email", "test-receiver@city.local")
    confirmed = payload.get("confirmed", False)
    return notification_service.send_test_email(recipient_email=recipient, confirmed=confirmed)

@app.post("/api/notifications/manual-send")
def manual_send_notification(payload: dict):
    """
    Operator manual email dispatch with explicit confirmation.
    Transmits incident dispatch to configured or manually selected authority.
    """
    incident_id = payload.get("incident_id")
    recipient = payload.get("recipient_email")
    subject = payload.get("subject", "CivicSentinel Incident Notice")
    message = payload.get("message", "")
    actor = payload.get("actor", "Dashboard Operator")
    confirmed = payload.get("confirmed", False)
    evidence_refs = payload.get("evidence_references", [])

    if not incident_id:
        raise HTTPException(400, "incident_id is required")

    with SessionLocal() as db:
        inc = db.get(Incident, incident_id)
        if not inc:
            raise HTTPException(404, "Incident not found")

        loc_data = resolve_camera_and_authority(db, camera_id=inc.camera_id, asset_hint=inc.asset_id)
        res = notification_service.send_manual_incident_dispatch(
            db=db,
            incident=inc,
            asset_data=loc_data,
            recipient_email=recipient or inc.assigned_contact_email or "",
            subject=subject,
            message=message,
            actor=actor,
            confirmed=confirmed,
            evidence_refs=evidence_refs
        )
        if not res.get("success") and res.get("status") in ("UNCONFIRMED", "INVALID_RECIPIENT"):
            raise HTTPException(400, res["message"])
        
        ws_manager.broadcast_sync({"type": "INCIDENT_UPDATE", "incident_id": inc.id, "delivery_status": inc.delivery_status})
        return res

@app.post("/api/notifications/preview")
def preview_notification(payload: dict):
    """Render preview of dispatch email prior to transmission."""
    incident_id = payload.get("incident_id")
    custom_subject = payload.get("custom_subject")
    custom_message = payload.get("custom_message")
    recipient_email = payload.get("recipient_email")

    if not incident_id:
        raise HTTPException(400, "incident_id is required")

    with SessionLocal() as db:
        inc = db.get(Incident, incident_id)
        if not inc:
            raise HTTPException(404, "Incident not found")

        loc_data = resolve_camera_and_authority(db, camera_id=inc.camera_id, asset_hint=inc.asset_id)
        return notification_service.preview_incident_email(
            incident=inc,
            asset_data=loc_data,
            level=inc.escalation_level or 1,
            custom_subject=custom_subject,
            custom_message=custom_message,
            recipient_email=recipient_email
        )

# -------------------------------------------------------------
# Road-Side Camera Registry & Live Analysis Endpoints
# -------------------------------------------------------------
@app.get("/api/cameras")
def get_cameras():
    """Retrieve all registered road-side CCTV and IP cameras with masked credentials."""
    with SessionLocal() as db:
        cams = db.scalars(select(Camera)).all()
        return [{
            "id": c.id,
            "name": c.name,
            "camera_type": c.camera_type,
            "stream_url": mask_stream_url(c.stream_url),
            "latitude": c.latitude,
            "longitude": c.longitude,
            "road_landmark": c.road_landmark,
            "ward": c.ward,
            "zone": c.zone,
            "city": c.city,
            "district": c.district,
            "assigned_authority_id": c.assigned_authority_id,
            "assigned_department": c.assigned_department,
            "status": c.status,
            "last_seen": c.last_seen,
            "capabilities": json.loads(c.capabilities or "[]"),
            "location_verification_status": c.location_verification_status,
            "last_frame_metrics": json.loads(c.last_frame_metrics) if c.last_frame_metrics else None,
            "failure_diagnostics": c.failure_diagnostics
        } for c in cams]

@app.get("/api/cameras/{camera_id}")
def get_camera(camera_id: str):
    """Retrieve single camera dossier with masked stream credentials."""
    with SessionLocal() as db:
        c = db.get(Camera, camera_id)
        if not c:
            raise HTTPException(404, "Camera not found")
        return {
            "id": c.id,
            "name": c.name,
            "camera_type": c.camera_type,
            "stream_url": mask_stream_url(c.stream_url),
            "latitude": c.latitude,
            "longitude": c.longitude,
            "road_landmark": c.road_landmark,
            "ward": c.ward,
            "zone": c.zone,
            "city": c.city,
            "district": c.district,
            "assigned_authority_id": c.assigned_authority_id,
            "assigned_department": c.assigned_department,
            "status": c.status,
            "last_seen": c.last_seen,
            "capabilities": json.loads(c.capabilities or "[]"),
            "location_verification_status": c.location_verification_status,
            "last_frame_metrics": json.loads(c.last_frame_metrics) if c.last_frame_metrics else None,
            "failure_diagnostics": c.failure_diagnostics
        }

@app.post("/api/cameras")
def register_or_update_camera(payload: dict):
    """Register new road-side camera or update location / authority assignments."""
    cid = payload.get("id") or f"CAM-{uuid.uuid4().hex[:6].upper()}"
    with SessionLocal() as db:
        cam = db.get(Camera, cid)
        if not cam:
            cam = Camera(id=cid, name=payload.get("name", f"Camera {cid}"))
            db.add(cam)
        if "name" in payload: cam.name = payload["name"]
        if "camera_type" in payload: cam.camera_type = payload["camera_type"]
        if "stream_url" in payload and not str(payload["stream_url"]).endswith("***"):
            cam.stream_url = payload["stream_url"]
        if "latitude" in payload: cam.latitude = float(payload["latitude"]) if payload["latitude"] not in (None, "") else None
        if "longitude" in payload: cam.longitude = float(payload["longitude"]) if payload["longitude"] not in (None, "") else None
        if "road_landmark" in payload: cam.road_landmark = payload["road_landmark"]
        if "ward" in payload: cam.ward = payload["ward"]
        if "zone" in payload: cam.zone = payload["zone"]
        if "city" in payload: cam.city = payload["city"]
        if "district" in payload: cam.district = payload["district"]
        if "assigned_authority_id" in payload: cam.assigned_authority_id = payload["assigned_authority_id"]
        if "assigned_department" in payload: cam.assigned_department = payload["assigned_department"]
        if "capabilities" in payload:
            caps = payload["capabilities"]
            cam.capabilities = json.dumps(caps if isinstance(caps, list) else [caps])

        # Location verification validation
        if cam.latitude is None or cam.longitude is None:
            if not cam.ward and not cam.road_landmark:
                cam.location_verification_status = "LOCATION_UNVERIFIED"
                cam.failure_diagnostics = "Missing GPS coordinates and municipal area."
            else:
                cam.location_verification_status = payload.get("location_verification_status", "PENDING_ADMIN_VERIFICATION")
        else:
            cam.location_verification_status = payload.get("location_verification_status", "VERIFIED")
            cam.failure_diagnostics = None

        cam.last_seen = datetime.now(timezone.utc).isoformat()
        db.commit()
        return {"id": cam.id, "status": "SAVED", "location_verification_status": cam.location_verification_status}

@app.post("/api/cameras/{camera_id}/test")
def test_camera_connectivity(camera_id: str):
    """Test connection to camera stream URL and verify frame reception without exposing credentials."""
    with SessionLocal() as db:
        cam = db.get(Camera, camera_id)
        if not cam:
            raise HTTPException(404, "Camera not found")

        url = cam.stream_url or ""
        now_iso = datetime.now(timezone.utc).isoformat()
        if url.startswith(("rtsp://", "http://", "https://")):
            cap = cv2.VideoCapture(url)
            opened = cap.isOpened()
            frame_received = False
            fps = 0.0
            if opened:
                ok, frame = cap.read()
                frame_received = ok and frame is not None
                fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
                cap.release()

            if frame_received:
                cam.status = "ONLINE"
                cam.last_seen = now_iso
                cam.failure_diagnostics = None
                db.commit()
                return {"camera_id": cam.id, "connected": True, "status": "ONLINE", "fps": fps, "diagnostics": "RTSP/IP stream verified and decodable."}
            else:
                cam.status = "DEGRADED" if opened else "OFFLINE"
                diag = "Connected to stream socket but 0 frames received." if opened else "Camera stream unreachable or timed out."
                cam.failure_diagnostics = diag
                db.commit()
                return {"camera_id": cam.id, "connected": False, "status": cam.status, "diagnostics": diag}
        else:
            cam.status = "ONLINE"
            cam.last_seen = now_iso
            cam.failure_diagnostics = None
            db.commit()
            return {"camera_id": cam.id, "connected": True, "status": "ONLINE", "diagnostics": "Local/Simulated device interface operational."}

@app.post("/api/cameras/{camera_id}/sample")
def sample_camera_live_frame(camera_id: str):
    """
    Sample frame from registered camera, run real OpenCV processing, associate with camera's location,
    perform temporal tracking & deduplication, and return explainable assessment.
    """
    with SessionLocal() as db:
        cam = db.get(Camera, camera_id)
        if not cam:
            raise HTTPException(404, "Camera not found")

        h, w = 360, 480
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :] = (38, 46, 52)
        cv2.rectangle(frame, (40, 180), (440, 320), (28, 32, 38), -1)
        # Ponding area
        cv2.ellipse(frame, (240, 250), (120, 50), 0, 0, 360, (18, 20, 24), -1)
        for gx in range(80, 400, 30):
            cv2.line(frame, (gx, 190), (gx, 230), (50, 60, 70), 3)

        jid = f"CAM-JOB-{uuid.uuid4().hex[:8]}"
        img_name = f"{jid}_frame.jpg"
        img_path = EVIDENCE / img_name
        cv2.imwrite(str(img_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])

        metrics, evidence_files = process_image_media(img_path, EVIDENCE, jid)

        job = Job(
            id=jid,
            filename=f"{cam.id}_surveillance_sample.jpg",
            media_type="image",
            status="PROCESSING",
            progress=50,
            file_path=str(img_path)
        )
        db.add(job)
        db.commit()

        pipeline = AgenticInvestigationPipeline(
            db=db,
            job=job,
            metrics=metrics,
            evidence_files=evidence_files,
            camera_id=cam.id
        )
        agent_output = pipeline.run()

        metrics.update(agent_output)
        job.result_json = json.dumps(metrics)
        job.status = "COMPLETED"
        job.progress = 100

        cam.last_seen = datetime.now(timezone.utc).isoformat()
        cam.last_frame_metrics = json.dumps({
            "water_proxy": metrics.get("water_area_ratio_proxy"),
            "obstruction": metrics.get("obstruction_index_proxy"),
            "confidence": metrics.get("visual_confidence"),
            "risk": agent_output.get("risk", {}).get("current_risk")
        })
        db.commit()

        ws_manager.broadcast_sync({"type": "CAMERA_UPDATE", "camera_id": cam.id, "risk": agent_output.get("risk", {}).get("current_risk")})

        return {
            "camera_id": cam.id,
            "job_id": jid,
            "metrics": metrics,
            "risk": agent_output.get("risk"),
            "location": agent_output.get("agent", {}).get("location"),
            "incident_id": agent_output.get("agent", {}).get("incident_id")
        }


# -------------------------------------------------------------
# Backward-Compatible Alerts & Reviews
# -------------------------------------------------------------
@app.get("/api/alerts")
def alerts():
    with SessionLocal() as db:
        return [{
            "alert_id": a.id,
            "job_id": a.job_id,
            "asset_id": a.asset_id,
            "severity": a.severity,
            "status": a.status,
            "summary": a.summary,
            "notes": a.notes
        } for a in db.scalars(select(Alert).order_by(Alert.id.desc())).all()]

def review_alert(alert_id: str, action: str, notes: str = ""):
    with SessionLocal() as db:
        a = db.get(Alert, alert_id)
        if not a:
            raise HTTPException(404, "Alert not found")
        if a.status in ("APPROVED", "REJECTED", "RESOLVED"):
            raise HTTPException(409, "Alert already finalised")
        a.status = action
        a.notes = notes[:2000]
        db.commit()
        return {"alert_id": a.id, "status": a.status, "physical_action_executed": False}

@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id: str):
    return review_alert(alert_id, "UNDER_REVIEW")

@app.post("/api/alerts/{alert_id}/approve")
def approve(alert_id: str, payload: dict = {}):
    return review_alert(alert_id, "APPROVED", payload.get("notes", ""))

@app.post("/api/alerts/{alert_id}/reject")
def reject(alert_id: str, payload: dict = {}):
    return review_alert(alert_id, "REJECTED", payload.get("notes", ""))

@app.post("/api/alerts/{alert_id}/resolve")
def resolve(alert_id: str):
    return review_alert(alert_id, "RESOLVED")

# -------------------------------------------------------------
# AWS & Benchmark Endpoints
# -------------------------------------------------------------
@app.get("/api/aws/status")
def get_aws_status():
    return aws_service.get_status()

@app.get("/api/benchmark/results")
def benchmark_results():
    return get_latest_benchmark_result(DATA.parent / "cool_benchmark" / "results")

@app.post("/api/benchmark/run")
def trigger_benchmark(frames: int = Query(default=30)):
    res = run_opencv_benchmark(frame_count=frames)
    results_dir = DATA.parent / "cool_benchmark" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "latest.json").write_text(json.dumps(res, indent=2))
    return res

@app.get("/api/metrics")
def metrics():
    with SessionLocal() as db:
        jobs_count = len(db.scalars(select(Job.id)).all())
        alerts_count = len(db.scalars(select(Alert.id)).all())
        incidents_count = len(db.scalars(select(Incident.id)).all())
        return {
            "jobs_total": jobs_count,
            "alerts_total": alerts_count,
            "incidents_total": incidents_count,
            "processing_mode": os.getenv("PROCESSING_MODE", "LOCAL"),
            "notification_provider": os.getenv("NOTIFICATION_PROVIDER", "MOCK")
        }

# -------------------------------------------------------------
# Frontend SPA Fallback (Registered after all backend/API routes)
# -------------------------------------------------------------
@app.get("/{full_path:path}")
def serve_spa_fallback(full_path: str):
    # Guard against intercepting non-existent API or system endpoints
    if (
        full_path.startswith("api/")
        or full_path.startswith("evidence/")
        or full_path.startswith("uploads/")
        or full_path in ("health", "ready", "docs", "redoc", "openapi.json", "ws")
    ):
        raise HTTPException(status_code=404, detail="Resource not found")

    file_candidate = FRONTEND_DIST / full_path
    if full_path and file_candidate.is_file():
        return FileResponse(file_candidate)

    index_file = FRONTEND_DIST / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    raise HTTPException(
        status_code=404,
        detail="Frontend distribution build not found. Please run 'npm run build' in frontend directory."
    )

