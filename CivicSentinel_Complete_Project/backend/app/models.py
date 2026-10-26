import os, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, String, Text, Integer, Float, Boolean, select, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA = Path(os.getenv("CIVICSENTINEL_DATA_DIR", ROOT / "data"))
UPLOADS = DATA / "uploads"
EVIDENCE = DATA / "evidence"
UPLOADS.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)

DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA / 'civicsentinel.db').as_posix()}")
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    filename: Mapped[str] = mapped_column(String)
    media_type: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="QUEUED")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now(timezone.utc).isoformat())
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str] = mapped_column(Text)

class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    asset_type: Mapped[str | None] = mapped_column(String, nullable=True, default="stormwater_drain")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True, default="Metro City")
    ward: Mapped[str | None] = mapped_column(String, nullable=True, default="Ward 4")
    jurisdiction: Mapped[str | None] = mapped_column(String, nullable=True, default="Municipal Corporation")
    department: Mapped[str | None] = mapped_column(String, nullable=True, default="Stormwater & Drainage Dept")
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    supervisor_email: Mapped[str | None] = mapped_column(String, nullable=True)
    director_email: Mapped[str | None] = mapped_column(String, nullable=True)
    current_risk: Mapped[str] = mapped_column(String, default="UNKNOWN")
    latest_job_id: Mapped[str] = mapped_column(String, default="")
    summary: Mapped[str] = mapped_column(Text, default="{}")

class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String)
    asset_id: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="PENDING_REVIEW")
    summary: Mapped[str] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    asset_id: Mapped[str] = mapped_column(String, index=True)
    camera_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    job_id: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String)  # LOW, MEDIUM, HIGH, CRITICAL, UNKNOWN
    status: Mapped[str] = mapped_column(String, default="DETECTED")
    # States: DETECTED, VALIDATED, NOTIFICATION_PENDING, NOTIFIED, ACKNOWLEDGED,
    #         ACTION_IN_PROGRESS, RESOLVED, NOTIFICATION_FAILED, ESCALATION_PENDING,
    #         ESCALATED, REJECTED_AS_FALSE_ALARM, NEEDS_HUMAN_REVIEW, UNASSIGNED
    location_verification_status: Mapped[str] = mapped_column(String, default="VERIFIED")
    road_landmark: Mapped[str | None] = mapped_column(String, nullable=True)
    zone: Mapped[str | None] = mapped_column(String, nullable=True)
    district: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_status: Mapped[str] = mapped_column(String, default="NEW")
    last_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_evidence: Mapped[str] = mapped_column(Text, default="{}")
    temporal_trend: Mapped[str] = mapped_column(String, default="unknown")
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_explanation: Mapped[str] = mapped_column(Text, default="")
    recommended_action: Mapped[str] = mapped_column(Text, default="")
    assigned_authority_id: Mapped[str | None] = mapped_column(String, nullable=True)
    assigned_department: Mapped[str | None] = mapped_column(String, nullable=True)
    assigned_contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    acknowledgement_token: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    acknowledgement_deadline: Mapped[str | None] = mapped_column(String, nullable=True)
    acknowledged_at: Mapped[str | None] = mapped_column(String, nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String, nullable=True)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    escalation_deadline: Mapped[str | None] = mapped_column(String, nullable=True)
    escalated_at: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Mapped[str | None] = mapped_column(String, nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_trail: Mapped[str] = mapped_column(Text, default="[]")

class Camera(Base):
    __tablename__ = "cameras"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    camera_type: Mapped[str] = mapped_column(String, default="IP")  # CCTV, IP, PTZ, FIXED, BROWSER
    stream_url: Mapped[str] = mapped_column(Text, default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    road_landmark: Mapped[str | None] = mapped_column(String, nullable=True)
    ward: Mapped[str | None] = mapped_column(String, nullable=True)
    zone: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True, default="Metro City")
    district: Mapped[str | None] = mapped_column(String, nullable=True)
    assigned_authority_id: Mapped[str | None] = mapped_column(String, nullable=True)
    assigned_department: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="ONLINE")  # ONLINE, OFFLINE, DEGRADED, TESTING
    last_seen: Mapped[str | None] = mapped_column(String, nullable=True)
    capabilities: Mapped[str] = mapped_column(Text, default='["rising_water","drain_overflow","drainage_obstruction","water_accumulation"]')
    location_verification_status: Mapped[str] = mapped_column(String, default="VERIFIED")  # VERIFIED, LOCATION_UNVERIFIED, PENDING_ADMIN_VERIFICATION
    last_frame_metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_diagnostics: Mapped[str | None] = mapped_column(Text, nullable=True)

class AuthorityConfig(Base):
    __tablename__ = "authority_configs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    ward: Mapped[str] = mapped_column(String)
    jurisdiction: Mapped[str] = mapped_column(String)
    department: Mapped[str] = mapped_column(String)
    level_1_name: Mapped[str] = mapped_column(String)
    level_1_email: Mapped[str] = mapped_column(String)
    level_2_name: Mapped[str] = mapped_column(String)
    level_2_email: Mapped[str] = mapped_column(String)
    level_3_name: Mapped[str] = mapped_column(String)
    level_3_email: Mapped[str] = mapped_column(String)
    escalation_delay_minutes: Mapped[int] = mapped_column(Integer, default=15)
    critical_delay_minutes: Mapped[int] = mapped_column(Integer, default=5)
    active: Mapped[int] = mapped_column(Integer, default=1)

class NotificationAudit(Base):
    __tablename__ = "notification_audits"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    incident_id: Mapped[str] = mapped_column(String, index=True)
    recipient: Mapped[str] = mapped_column(String)
    level: Mapped[int] = mapped_column(Integer, default=1)
    channel: Mapped[str] = mapped_column(String)  # LOCAL_MOCK, SMTP, AWS_SES
    subject: Mapped[str] = mapped_column(String)
    body_preview: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String)  # SENT, FAILED, SIMULATED
    provider_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[str] = mapped_column(String, default=lambda: datetime.now(timezone.utc).isoformat())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String, default="SYSTEM")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[str] = mapped_column(String, default=lambda: datetime.now(timezone.utc).isoformat())

import re

def mask_stream_url(url: str | None) -> str:
    """Mask credentials in RTSP or HTTP stream URLs so secrets are never exposed in frontend or logs."""
    if not url:
        return ""
    # Matches ://username:password@host
    return re.sub(r"://([^:@/]+):(.*)@([a-zA-Z0-9._~-]+(?::[0-9]+)?/?)", r"://\1:***@\3", url)

def init_db():
    Base.metadata.create_all(engine)
    # Perform additive migrations for existing tables if needed
    with engine.begin() as conn:
        inspector = inspect(conn)
        columns = [c["name"] for c in inspector.get_columns("assets")]
        additive_cols = [
            ("name", "VARCHAR"),
            ("asset_type", "VARCHAR DEFAULT 'stormwater_drain'"),
            ("latitude", "FLOAT"),
            ("longitude", "FLOAT"),
            ("address", "VARCHAR"),
            ("city", "VARCHAR DEFAULT 'Metro City'"),
            ("ward", "VARCHAR DEFAULT 'Ward 4'"),
            ("jurisdiction", "VARCHAR DEFAULT 'Municipal Corporation'"),
            ("department", "VARCHAR DEFAULT 'Stormwater & Drainage Dept'"),
            ("contact_email", "VARCHAR"),
            ("supervisor_email", "VARCHAR"),
            ("director_email", "VARCHAR"),
        ]
        for col_name, col_type in additive_cols:
            if col_name not in columns:
                try:
                    conn.execute(text(f"ALTER TABLE assets ADD COLUMN {col_name} {col_type}"))
                except Exception:
                    pass

        inc_columns = [c["name"] for c in inspector.get_columns("incidents")]
        additive_inc_cols = [
            ("camera_id", "VARCHAR"),
            ("location_verification_status", "VARCHAR DEFAULT 'VERIFIED'"),
            ("road_landmark", "VARCHAR"),
            ("zone", "VARCHAR"),
            ("district", "VARCHAR"),
            ("delivery_status", "VARCHAR DEFAULT 'NEW'"),
            ("last_response", "TEXT"),
        ]
        for col_name, col_type in additive_inc_cols:
            if col_name not in inc_columns:
                try:
                    conn.execute(text(f"ALTER TABLE incidents ADD COLUMN {col_name} {col_type}"))
                except Exception:
                    pass

    # Seed default authorities if empty
    with SessionLocal() as db:
        if not db.scalars(select(AuthorityConfig)).first():
            default_authorities = [
                AuthorityConfig(
                    id="AUTH-WARD-04",
                    name="Ward 4 Drainage Division",
                    ward="Ward 4",
                    jurisdiction="Central Municipality",
                    department="Municipal Stormwater & Flood Control",
                    level_1_name="Field Drainage Response Crew 4A",
                    level_1_email=os.getenv("WARD4_CREW_EMAIL", "ward4-drainage-crew@city-civicsentinel.local"),
                    level_2_name="District Infrastructure Engineer",
                    level_2_email=os.getenv("DISTRICT_ENGINEER_EMAIL", "district-engineer@city-civicsentinel.local"),
                    level_3_name="Municipal Emergency Operations Control",
                    level_3_email=os.getenv("MUNICIPAL_DISASTER_EMAIL", "emergency-ops@city-civicsentinel.local"),
                    escalation_delay_minutes=int(os.getenv("ESCALATION_DELAY_MINUTES", "15")),
                    critical_delay_minutes=int(os.getenv("CRITICAL_DELAY_MINUTES", "5")),
                    active=1
                ),
                AuthorityConfig(
                    id="AUTH-WARD-11",
                    name="Ward 11 Lowland Waterway Authority",
                    ward="Ward 11",
                    jurisdiction="Riverside District",
                    department="Waterway & Culvert Maintenance",
                    level_1_name="Lowland Culvert Inspector Unit",
                    level_1_email="ward11-inspector@city-civicsentinel.local",
                    level_2_name="Riverside Zone Superintendent",
                    level_2_email="riverside-superintendent@city-civicsentinel.local",
                    level_3_name="Director of Municipal Public Works",
                    level_3_email="public-works-director@city-civicsentinel.local",
                    escalation_delay_minutes=15,
                    critical_delay_minutes=5,
                    active=1
                )
            ]
            db.add_all(default_authorities)
            db.commit()

        # Seed default assets using merge so standard infrastructure assets always exist
        seed_assets = [
            Asset(
                id="ASSET-W4-CULVERT12",
                name="Market Crossing Main Culvert #12",
                asset_type="box_culvert",
                latitude=12.9716,
                longitude=77.5946,
                address="Crossing of 4th Cross & Commercial Rd, Ward 4",
                city="Metro City",
                ward="Ward 4",
                jurisdiction="Central Municipality",
                department="Municipal Stormwater & Flood Control",
                contact_email="ward4-drainage-crew@city-civicsentinel.local",
                supervisor_email="district-engineer@city-civicsentinel.local",
                director_email="emergency-ops@city-civicsentinel.local",
                current_risk="LOW",
                latest_job_id="",
                summary=json.dumps({"risk": {"current_risk": "LOW"}, "trend": "stable"})
            ),
            Asset(
                id="ASSET-W4-DRAIN08",
                name="North Avenue Stormwater Intake #8",
                asset_type="curb_inlet",
                latitude=12.9740,
                longitude=77.5980,
                address="North Avenue near Metro Station Entrance",
                city="Metro City",
                ward="Ward 4",
                jurisdiction="Central Municipality",
                department="Municipal Stormwater & Flood Control",
                contact_email="ward4-drainage-crew@city-civicsentinel.local",
                supervisor_email="district-engineer@city-civicsentinel.local",
                director_email="emergency-ops@city-civicsentinel.local",
                current_risk="LOW",
                latest_job_id="",
                summary=json.dumps({"risk": {"current_risk": "LOW"}, "trend": "stable"})
            ),
            Asset(
                id="ASSET-W11-OUTFALL02",
                name="Riverside Highway Discharge Outfall #2",
                asset_type="tidal_outfall",
                latitude=12.9620,
                longitude=77.6100,
                address="Riverside Expressway km 14.2 Embankment",
                city="Metro City",
                ward="Ward 11",
                jurisdiction="Riverside District",
                department="Waterway & Culvert Maintenance",
                contact_email="ward11-inspector@city-civicsentinel.local",
                supervisor_email="riverside-superintendent@city-civicsentinel.local",
                director_email="public-works-director@city-civicsentinel.local",
                current_risk="LOW",
                latest_job_id="",
                summary=json.dumps({"risk": {"current_risk": "LOW"}, "trend": "stable"})
            )
        ]
        for a in seed_assets:
            existing = db.get(Asset, a.id)
            if not existing:
                db.add(a)
        db.commit()

        # Seed registered road-side cameras
        if not db.scalars(select(Camera)).first():
            seed_cams = [
                Camera(
                    id="CAM-01",
                    name="Market Crossing Canal CCTV #1",
                    camera_type="CCTV",
                    stream_url="rtsp://cctv-stream.local/market-crossing-sluice-a",
                    latitude=12.9716,
                    longitude=77.5946,
                    road_landmark="Commercial Road & 4th Cross",
                    ward="Ward 4",
                    zone="Central Zone",
                    city="Metro City",
                    district="Central District",
                    assigned_authority_id="AUTH-WARD-04",
                    assigned_department="Municipal Stormwater & Flood Control",
                    status="ONLINE",
                    last_seen=datetime.now(timezone.utc).isoformat(),
                    capabilities=json.dumps(["rising_water", "drain_overflow", "drainage_obstruction", "water_accumulation"]),
                    location_verification_status="VERIFIED"
                ),
                Camera(
                    id="CAM-02",
                    name="North Avenue Inflow PTZ #2",
                    camera_type="PTZ",
                    stream_url="rtsp://cctv-stream.local/north-ave-culvert-14",
                    latitude=12.9740,
                    longitude=77.5980,
                    road_landmark="North Avenue near Metro Entrance",
                    ward="Ward 4",
                    zone="Central Zone",
                    city="Metro City",
                    district="Central District",
                    assigned_authority_id="AUTH-WARD-04",
                    assigned_department="Municipal Stormwater & Flood Control",
                    status="ONLINE",
                    last_seen=datetime.now(timezone.utc).isoformat(),
                    capabilities=json.dumps(["rising_water", "drain_overflow", "drainage_obstruction", "water_accumulation"]),
                    location_verification_status="VERIFIED"
                ),
                Camera(
                    id="CAM-03",
                    name="Riverside Outfall Fixed IP #3",
                    camera_type="IP",
                    stream_url="http://ip-cam.local/riverside-outfall-02",
                    latitude=12.9620,
                    longitude=77.6100,
                    road_landmark="Riverside Expressway km 14.2",
                    ward="Ward 11",
                    zone="Riverside Zone",
                    city="Metro City",
                    district="Riverside District",
                    assigned_authority_id="AUTH-WARD-11",
                    assigned_department="Waterway & Culvert Maintenance",
                    status="ONLINE",
                    last_seen=datetime.now(timezone.utc).isoformat(),
                    capabilities=json.dumps(["rising_water", "drain_overflow", "drainage_obstruction", "water_accumulation"]),
                    location_verification_status="VERIFIED"
                ),
                Camera(
                    id="CAM-UNVERIFIED-01",
                    name="Industrial Corridor Sub-Drain 9 (Pending Survey)",
                    camera_type="IP",
                    stream_url="rtsp://cctv-stream.local/industrial-unverified-drain9",
                    latitude=None,
                    longitude=None,
                    road_landmark="Unsurveyed Industrial Sector 7 Lateral",
                    ward=None,
                    zone=None,
                    city="Metro City",
                    district=None,
                    assigned_authority_id=None,
                    assigned_department=None,
                    status="TESTING",
                    last_seen=datetime.now(timezone.utc).isoformat(),
                    capabilities=json.dumps(["rising_water", "drainage_obstruction", "water_accumulation"]),
                    location_verification_status="LOCATION_UNVERIFIED",
                    failure_diagnostics="GPS coordinates not configured. Administrator verification required before authority dispatch."
                )
            ]
            db.add_all(seed_cams)
            db.commit()
