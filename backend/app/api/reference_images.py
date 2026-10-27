"""Admin-only camera reference-image upload and protected binary retrieval."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.config import get_settings
from app.core.errors import APIError
from app.db.session import get_db
from app.models import AuditLog, Camera, ParkingSpot, User
from app.schemas.parking import CameraOut
from app.services.reference_images import (
    locate_reference_image,
    save_reference_image,
    validate_reference_image,
)

router = APIRouter(prefix="/cameras", tags=["camera-reference-images"])
reader = require_roles("admin", "operator")
writer = require_roles("admin")


@router.put("/{camera_id}/reference-image", response_model=CameraOut)
def upload_reference_image(
    camera_id: UUID,
    expected_camera_config_version: int = Form(ge=1),
    image: UploadFile = File(...),
    user: User = Depends(writer),
    db: Session = Depends(get_db),
):
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise APIError(404, "CAMERA_NOT_FOUND", "Camera not found")
    if camera.config_version != expected_camera_config_version:
        raise APIError(409, "CAMERA_VERSION_CONFLICT", "Camera configuration changed; reload and retry")
    # Polygon coordinates refer to a fixed image. Replacing it invalidates those
    # coordinates; callers must deactivate old spots and redraw them afterwards.
    active_spot = db.scalar(select(ParkingSpot.id).where(
        ParkingSpot.camera_id == camera_id,
        ParkingSpot.is_active.is_(True),
    ).limit(1))
    if active_spot is not None:
        raise APIError(409, "ACTIVE_SPOTS_EXIST", "Deactivate active spots before changing the reference image")

    limit_mb = get_settings().upload_max_mb
    if not 1 <= limit_mb <= 100:
        raise APIError(503, "UPLOAD_NOT_CONFIGURED", "Invalid upload size limit")
    # Read at most limit + 1 bytes instead of trusting Content-Length.
    try:
        content = image.file.read(limit_mb * 1024 * 1024 + 1)
    finally:
        image.file.close()
    width, height, extension = validate_reference_image(content, image.content_type)
    key, saved_file = save_reference_image(camera_id, content, extension)
    try:
        result = db.execute(
            update(Camera)
            .where(Camera.id == camera_id, Camera.config_version == expected_camera_config_version)
            .values(
                reference_image_path=key,
                reference_width=width,
                reference_height=height,
                config_version=Camera.config_version + 1,
            )
        )
        if result.rowcount != 1:
            db.rollback()
            raise APIError(409, "CAMERA_VERSION_CONFLICT", "Camera configuration changed; reload and retry")
        db.add(AuditLog(actor_id=user.id, action="camera.reference_image_updated", entity_type="camera", entity_id=camera_id))
        db.commit()
        db.refresh(camera)
    except Exception:
        db.rollback()
        saved_file.unlink(missing_ok=True)
        raise
    # Prior image files are retained to avoid silently losing prior reference frames.
    return camera


@router.get("/{camera_id}/reference-image", response_class=FileResponse)
def get_reference_image(camera_id: UUID, _user: User = Depends(reader), db: Session = Depends(get_db)):
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise APIError(404, "CAMERA_NOT_FOUND", "Camera not found")
    path = locate_reference_image(camera_id, camera.reference_image_path)
    return FileResponse(
        path,
        media_type="image/jpeg" if path.suffix == ".jpg" else "image/png",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
