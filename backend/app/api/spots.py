"""FR-03/04: parking spot polygon management, optimistic camera-version updates."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.errors import APIError
from app.db.session import get_db
from app.models import AuditLog, Camera, ParkingSpot, User
from app.schemas.spots import SpotCreate, SpotList, SpotOut, SpotPatch

router = APIRouter(tags=["spots"])
reader = require_roles("admin", "operator")
writer = require_roles("admin")
MAX_ACTIVE_SPOTS = 100  # AI service limit, enforced before adding a spot.


def camera_or_404(db: Session, camera_id: UUID) -> Camera:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise APIError(404, "CAMERA_NOT_FOUND", "Camera not found")
    return camera


def spot_or_404(db: Session, spot_id: UUID) -> ParkingSpot:
    spot = db.get(ParkingSpot, spot_id)
    if spot is None:
        raise APIError(404, "SPOT_NOT_FOUND", "Parking spot not found")
    return spot


def verify_version(camera: Camera, expected: int) -> None:
    if camera.config_version != expected:
        raise APIError(409, "CAMERA_VERSION_CONFLICT", "Camera configuration changed; reload and retry")


def advance_version(db: Session, camera_id: UUID, expected: int) -> int:
    # The conditional UPDATE serializes concurrent writes on PostgreSQL.
    updated = db.execute(
        update(Camera)
        .where(Camera.id == camera_id, Camera.config_version == expected)
        .values(config_version=Camera.config_version + 1)
    )
    if updated.rowcount != 1:
        db.rollback()
        raise APIError(409, "CAMERA_VERSION_CONFLICT", "Camera configuration changed; reload and retry")
    return expected + 1


def to_out(spot: ParkingSpot, version: int) -> SpotOut:
    return SpotOut(
        id=spot.id, camera_id=spot.camera_id, spot_code=spot.spot_code,
        polygon=spot.polygon, is_active=spot.is_active,
        camera_config_version=version,
    )


def duplicate_code(db: Session, camera_id: UUID, code: str, exclude: UUID | None = None) -> bool:
    stmt = select(ParkingSpot.id).where(ParkingSpot.camera_id == camera_id, ParkingSpot.spot_code == code)
    if exclude is not None:
        stmt = stmt.where(ParkingSpot.id != exclude)
    return db.scalar(stmt.limit(1)) is not None


@router.get("/cameras/{camera_id}/spots", response_model=SpotList)
def list_spots(camera_id: UUID, include_inactive: bool = False,
               _user: User = Depends(reader), db: Session = Depends(get_db)):
    camera = camera_or_404(db, camera_id)
    stmt = select(ParkingSpot).where(ParkingSpot.camera_id == camera_id)
    if not include_inactive:
        stmt = stmt.where(ParkingSpot.is_active.is_(True))
    spots = db.scalars(stmt.order_by(ParkingSpot.spot_code, ParkingSpot.id)).all()
    return SpotList(items=[to_out(s, camera.config_version) for s in spots],
                    total=len(spots), camera_config_version=camera.config_version)


@router.post("/cameras/{camera_id}/spots", status_code=201, response_model=SpotOut)
def create_spot(camera_id: UUID, payload: SpotCreate,
                user: User = Depends(writer), db: Session = Depends(get_db)):
    camera = camera_or_404(db, camera_id)
    expected = payload.expected_camera_config_version
    verify_version(camera, expected)
    if duplicate_code(db, camera_id, payload.spot_code):
        raise APIError(409, "SPOT_CODE_CONFLICT", "Spot code already exists in this camera")
    total = db.scalar(select(func.count()).select_from(ParkingSpot).where(
        ParkingSpot.camera_id == camera_id, ParkingSpot.is_active.is_(True))) or 0
    if total >= MAX_ACTIVE_SPOTS:
        raise APIError(409, "CAMERA_SPOT_LIMIT", "Camera cannot exceed 100 active spots")
    polygon = [p.model_dump() for p in payload.polygon]
    version = advance_version(db, camera_id, expected)
    spot = ParkingSpot(camera_id=camera_id, spot_code=payload.spot_code, polygon=polygon)
    db.add(spot)
    try:
        db.flush()
        db.add(AuditLog(actor_id=user.id, action="spot.created", entity_type="parking_spot", entity_id=spot.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise APIError(409, "SPOT_CODE_CONFLICT", "Spot code already exists in this camera") from None
    db.refresh(spot)
    return to_out(spot, version)


@router.patch("/spots/{spot_id}", response_model=SpotOut)
def patch_spot(spot_id: UUID, payload: SpotPatch,
               user: User = Depends(writer), db: Session = Depends(get_db)):
    spot = spot_or_404(db, spot_id)
    camera = camera_or_404(db, spot.camera_id)
    expected = payload.expected_camera_config_version
    verify_version(camera, expected)
    if not spot.is_active:
        raise APIError(409, "SPOT_INACTIVE", "Inactive spots cannot be edited")
    code = payload.spot_code if payload.spot_code is not None else spot.spot_code
    polygon = [p.model_dump() for p in payload.polygon] if payload.polygon is not None else spot.polygon
    if code == spot.spot_code and polygon == spot.polygon:
        return to_out(spot, expected)
    if code != spot.spot_code and duplicate_code(db, spot.camera_id, code, spot.id):
        raise APIError(409, "SPOT_CODE_CONFLICT", "Spot code already exists in this camera")
    version = advance_version(db, spot.camera_id, expected)
    spot.spot_code, spot.polygon = code, polygon
    db.add(AuditLog(actor_id=user.id, action="spot.updated", entity_type="parking_spot", entity_id=spot.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise APIError(409, "SPOT_CODE_CONFLICT", "Spot code already exists in this camera") from None
    db.refresh(spot)
    return to_out(spot, version)


@router.delete("/spots/{spot_id}", status_code=204)
def deactivate_spot(spot_id: UUID, expected_camera_config_version: int = Query(ge=1),
                    user: User = Depends(writer), db: Session = Depends(get_db)) -> Response:
    spot = spot_or_404(db, spot_id)
    camera = camera_or_404(db, spot.camera_id)
    verify_version(camera, expected_camera_config_version)
    if not spot.is_active:
        raise APIError(409, "SPOT_INACTIVE", "Parking spot is already inactive")
    advance_version(db, spot.camera_id, expected_camera_config_version)
    spot.is_active = False
    db.add(AuditLog(actor_id=user.id, action="spot.deactivated", entity_type="parking_spot", entity_id=spot.id))
    db.commit()
    return Response(status_code=204)
