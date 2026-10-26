"""FR-02: camera CRUD with monotonically increasing config versions."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.errors import APIError
from app.db.session import get_db
from app.models import AuditLog, Camera, ParkingLot, User
from app.schemas.parking import CameraCreate, CameraOut, CameraPage, CameraPatch

router = APIRouter(prefix="/cameras", tags=["cameras"])
reader = require_roles("admin", "operator")
writer = require_roles("admin")


def find_camera(db: Session, camera_id: UUID) -> Camera:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise APIError(404, "CAMERA_NOT_FOUND", "Camera not found")
    return camera


@router.get("", response_model=CameraPage)
def list_cameras(
    parking_lot_id: UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(reader),
    db: Session = Depends(get_db),
):
    where = Camera.parking_lot_id == parking_lot_id if parking_lot_id is not None else True
    total = db.scalar(select(func.count()).select_from(Camera).where(where)) or 0
    cameras = db.scalars(select(Camera).where(where).order_by(Camera.name, Camera.id).limit(limit).offset(offset)).all()
    return CameraPage(items=cameras, total=total, limit=limit, offset=offset)


@router.post("", status_code=201, response_model=CameraOut)
def create_camera(payload: CameraCreate, user: User = Depends(writer), db: Session = Depends(get_db)):
    if db.get(ParkingLot, payload.parking_lot_id) is None:
        raise APIError(404, "PARKING_LOT_NOT_FOUND", "Parking lot not found")
    camera = Camera(**payload.model_dump())
    db.add(camera)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="camera.created", entity_type="camera", entity_id=camera.id))
    db.commit()
    db.refresh(camera)
    return camera


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: UUID, _user: User = Depends(reader), db: Session = Depends(get_db)):
    return find_camera(db, camera_id)


@router.patch("/{camera_id}", response_model=CameraOut)
def patch_camera(camera_id: UUID, payload: CameraPatch, user: User = Depends(writer), db: Session = Depends(get_db)):
    camera = find_camera(db, camera_id)
    if payload.expected_camera_config_version is not None and payload.expected_camera_config_version != camera.config_version:
        raise APIError(409, "CAMERA_VERSION_CONFLICT", "Camera configuration was modified; reload and retry")
    if camera.name == payload.name:
        return camera
    # Atomic compare-and-swap prevents losing an update made by another admin.
    updated = db.execute(
        update(Camera)
        .where(Camera.id == camera.id, Camera.config_version == camera.config_version)
        .values(name=payload.name, config_version=Camera.config_version + 1)
    )
    if updated.rowcount != 1:
        db.rollback()
        raise APIError(409, "CAMERA_VERSION_CONFLICT", "Camera configuration was modified; reload and retry")
    db.add(AuditLog(actor_id=user.id, action="camera.updated", entity_type="camera", entity_id=camera.id))
    db.commit()
    db.refresh(camera)
    return camera
