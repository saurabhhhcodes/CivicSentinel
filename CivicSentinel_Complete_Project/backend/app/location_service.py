import math, json
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Asset, AuthorityConfig, Camera

def calculate_haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two GPS coordinates in kilometers."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def resolve_camera_and_authority(
    db: Session,
    camera_id: str | None = None,
    asset_hint: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    road: str | None = None,
    ward: str | None = None,
    zone: str | None = None
) -> dict:
    """
    Resolve camera/monitored infrastructure identity, verified location, and responsible authority.
    STRICT RULE: Never uses personal physical location, laptop GPS, browser geolocation, or IP address.
    
    Priority Hierarchy:
    1. GPS coordinates supplied by camera or its authorised integration (lat, lon parameters).
    2. Coordinates configured by administrator for a registered camera.
    3. Coordinates and jurisdiction associated with the camera's registered asset.
    4. A configured road, ward, zone, or municipal area when exact coordinates are unavailable.
    
    If location or authority is uncertain/missing, returns status LOCATION_UNVERIFIED and UNASSIGNED.
    """
    camera: Camera | None = None
    asset: Asset | None = None
    resolved_lat: float | None = None
    resolved_lon: float | None = None
    resolved_road: str | None = road
    resolved_ward: str | None = ward
    resolved_zone: str | None = zone
    resolved_city: str = "Metro City"
    resolved_district: str | None = None
    resolved_dept: str | None = None
    verification_status = "VERIFIED"
    verification_reason = ""

    # Check registered Camera if provided
    if camera_id:
        camera = db.get(Camera, camera_id)
        if camera:
            if camera.location_verification_status == "LOCATION_UNVERIFIED":
                verification_status = "LOCATION_UNVERIFIED"
                verification_reason = camera.failure_diagnostics or "Camera marked LOCATION_UNVERIFIED by administrator."

    # Priority 1: Direct telemetry GPS supplied by camera / integration
    if lat is not None and lon is not None:
        resolved_lat = float(lat)
        resolved_lon = float(lon)
    # Priority 2: Admin configured coordinates for registered camera
    elif camera and camera.latitude is not None and camera.longitude is not None:
        resolved_lat = float(camera.latitude)
        resolved_lon = float(camera.longitude)

    # Resolve Camera metadata (Priority 4 attributes)
    if camera:
        if not resolved_road:
            resolved_road = camera.road_landmark
        if not resolved_ward:
            resolved_ward = camera.ward
        if not resolved_zone:
            resolved_zone = camera.zone
        if camera.city:
            resolved_city = camera.city
        if camera.district:
            resolved_district = camera.district
        if camera.assigned_department:
            resolved_dept = camera.assigned_department

    # Priority 3: Asset registered with camera or nearest asset within 1.5km
    if asset_hint:
        asset = db.get(Asset, asset_hint)

    if not asset and resolved_lat is not None and resolved_lon is not None:
        candidates = db.scalars(select(Asset).where(Asset.latitude.isnot(None), Asset.longitude.isnot(None))).all()
        best_candidate = None
        min_dist = float("inf")
        for cand in candidates:
            if cand.latitude is not None and cand.longitude is not None:
                dist = calculate_haversine_km(resolved_lat, resolved_lon, cand.latitude, cand.longitude)
                if dist < min_dist and dist <= 1.5:  # Within 1.5km
                    min_dist = dist
                    best_candidate = cand
        if best_candidate:
            asset = best_candidate

    if asset:
        if resolved_lat is None:
            resolved_lat = asset.latitude
        if resolved_lon is None:
            resolved_lon = asset.longitude
        if not resolved_road:
            resolved_road = asset.address
        if not resolved_ward:
            resolved_ward = asset.ward
        if not resolved_dept:
            resolved_dept = asset.department
        if not resolved_district:
            resolved_district = asset.jurisdiction

    # If camera or asset has not resolved ward or coordinates, check if location is unverified
    if not resolved_lat and not resolved_lon and not resolved_ward and not resolved_road:
        verification_status = "LOCATION_UNVERIFIED"
        verification_reason = "Missing camera coordinates and unmapped municipal ward. Administrator verification required."

    # Resolve responsible Authority from verified Ward / Jurisdiction
    auth_config: AuthorityConfig | None = None
    if resolved_ward and verification_status != "LOCATION_UNVERIFIED":
        auth_config = db.scalars(
            select(AuthorityConfig).where(AuthorityConfig.ward == resolved_ward, AuthorityConfig.active == 1)
        ).first()

    auth_info = None
    if auth_config and auth_config.level_1_email:
        auth_info = {
            "authority_id": auth_config.id,
            "name": auth_config.name,
            "ward": auth_config.ward,
            "jurisdiction": auth_config.jurisdiction,
            "department": auth_config.department,
            "level_1_name": auth_config.level_1_name,
            "level_1_email": auth_config.level_1_email,
            "level_2_name": auth_config.level_2_name,
            "level_2_email": auth_config.level_2_email,
            "level_3_name": auth_config.level_3_name,
            "level_3_email": auth_config.level_3_email,
            "escalation_delay_minutes": auth_config.escalation_delay_minutes,
            "critical_delay_minutes": auth_config.critical_delay_minutes,
            "assigned_status": "ASSIGNED"
        }
        if not resolved_dept:
            resolved_dept = auth_config.department
    else:
        # Authority unassigned or unverified
        if verification_status == "VERIFIED":
            # If location had ward but authority is not configured in DB
            auth_info = {
                "authority_id": "AUTH-UNASSIGNED",
                "name": "Unassigned Authority (Pending Jurisdiction Mapping)",
                "ward": resolved_ward or "Unknown Ward",
                "jurisdiction": resolved_district or "Unassigned District",
                "department": resolved_dept or "Stormwater & Drainage Dept",
                "level_1_name": "Pending Assignment",
                "level_1_email": "",
                "level_2_name": "Pending Assignment",
                "level_2_email": "",
                "level_3_name": "Pending Assignment",
                "level_3_email": "",
                "escalation_delay_minutes": 15,
                "critical_delay_minutes": 5,
                "assigned_status": "UNASSIGNED"
            }
        else:
            auth_info = {
                "authority_id": "AUTH-UNVERIFIED",
                "name": "Location Unverified - Authority Unassigned",
                "ward": "Unverified",
                "jurisdiction": "Unverified",
                "department": "Pending Administrative Verification",
                "level_1_name": "N/A",
                "level_1_email": "",
                "level_2_name": "N/A",
                "level_2_email": "",
                "level_3_name": "N/A",
                "level_3_email": "",
                "escalation_delay_minutes": 15,
                "critical_delay_minutes": 5,
                "assigned_status": "UNASSIGNED"
            }

    return {
        "camera_id": camera.id if camera else (camera_id or "CAM-DEFAULT"),
        "camera_name": camera.name if camera else ("Default Monitored Feed" if not camera_id else camera_id),
        "asset_id": asset.id if asset else (asset_hint or "ASSET-UNASSIGNED"),
        "asset_name": asset.name if asset and asset.name else "Infrastructure Asset",
        "asset_type": asset.asset_type if asset and asset.asset_type else "drainage_culvert",
        "latitude": resolved_lat,
        "longitude": resolved_lon,
        "road_landmark": resolved_road or "Road/Landmark Pending Survey",
        "address": resolved_road or "Address Pending Verification",
        "ward": resolved_ward or "Unassigned Ward",
        "zone": resolved_zone or "Municipal Zone",
        "city": resolved_city,
        "district": resolved_district or "Central District",
        "jurisdiction": resolved_district or "Municipal District",
        "department": resolved_dept or "Municipal Stormwater & Drainage",
        "location_verification_status": verification_status,
        "verification_reason": verification_reason,
        "authority": auth_info
    }

# Backward compatibility alias
def resolve_asset_and_authority(db: Session, asset_hint: str | None = None, lat: float | None = None, lon: float | None = None) -> dict:
    """Backward-compatible entry point maintaining legacy signature while obeying priority rules."""
    return resolve_camera_and_authority(db=db, asset_hint=asset_hint, lat=lat, lon=lon)
