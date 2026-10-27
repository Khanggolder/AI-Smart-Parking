"""W4: accept a real snapshot, queue inference, inspect persistent job results."""
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.config import get_settings
from app.core.errors import APIError
from app.db.session import get_db
from app.models import AuditLog, Camera, ParkingSpot, Snapshot, SpotPrediction, User
from app.schemas.snapshots import PredictionOut, SnapshotAccepted, SnapshotOut, SnapshotPage, SummaryOut
from app.services.reference_images import locate_reference_image, validate_reference_image
from app.services.snapshot_jobs import run_snapshot_job
from app.services.snapshot_storage import save_snapshot, locate_snapshot

router = APIRouter(prefix="/snapshots", tags=["snapshots"])
reader = require_roles("admin", "operator")


def summary_from_predictions(predictions: list[PredictionOut]) -> SummaryOut:
    count = {key: 0 for key in ("empty", "occupied", "unknown")}
    for item in predictions:
        count[item.predicted_label] += 1
    total = len(predictions)
    if total == 0:
        status = "NO_SPOTS"
    elif count["empty"]:
        status = "AVAILABLE"
    elif count["unknown"]:
        status = "UNDETERMINED"
    else:
        status = "FULL"
    return SummaryOut(
        total=total, **count,
        occupancy_rate=round(count["occupied"] / total * 100, 2) if total else None,
        full=status == "FULL", status=status,
    )


@router.post("", status_code=202, response_model=SnapshotAccepted)
def create_snapshot(
    background_tasks: BackgroundTasks,
    camera_id: UUID = Form(...),
    captured_at: datetime = Form(...),
    image: UploadFile = File(...),
    user: User = Depends(reader),
    db: Session = Depends(get_db),
):
    if captured_at.utcoffset() is None:
        raise APIError(422, "INVALID_CAPTURED_AT", "captured_at must contain a timezone offset")
    # Serialize snapshot configuration capture with camera config updates.
    camera = db.scalar(select(Camera).where(Camera.id == camera_id).with_for_update())
    if camera is None:
        raise APIError(404, "CAMERA_NOT_FOUND", "Camera not found")
    # The image must be anchored to a real, configured camera reference frame.
    if not camera.reference_image_path or not camera.reference_width or not camera.reference_height:
        raise APIError(409, "CAMERA_NOT_CONFIGURED", "Upload a camera reference image first")
    locate_reference_image(camera_id, camera.reference_image_path)
    spots = db.scalars(select(ParkingSpot).where(
        ParkingSpot.camera_id == camera_id, ParkingSpot.is_active.is_(True)
    ).order_by(ParkingSpot.spot_code, ParkingSpot.id)).all()
    if not spots:
        raise APIError(409, "NO_ACTIVE_SPOTS", "Draw active parking spots for the camera first")
    if len(spots) > 100:
        raise APIError(409, "CAMERA_SPOT_LIMIT", "AI accepts at most 100 active spots")

    max_bytes = get_settings().upload_max_mb * 1024 * 1024
    try:
        data = image.file.read(max_bytes + 1)
    finally:
        image.file.close()
    width, height, extension = validate_reference_image(data, image.content_type)
    if (width, height) != (camera.reference_width, camera.reference_height):
        raise APIError(422, "IMAGE_DIMENSIONS_MISMATCH", "Snapshot dimensions differ from camera reference image")

    captured_at = captured_at.astimezone(timezone.utc)
    copied_spots = [
        {"id": str(spot.id), "spot_code": spot.spot_code,
         "polygon": [{"x": p["x"], "y": p["y"]} for p in spot.polygon]}
        for spot in spots
    ]
    snapshot_id = uuid4()
    key, disk_path = save_snapshot(snapshot_id, data, extension)
    item = Snapshot(
        id=snapshot_id, camera_id=camera_id, captured_at=captured_at,
        image_path=key, camera_config_version=camera.config_version,
        spots_at_capture=copied_spots, job_status="queued",
    )
    try:
        db.add(item)
        db.add(AuditLog(actor_id=user.id, action="snapshot.queued", entity_type="snapshot", entity_id=snapshot_id))
        db.commit()
        db.refresh(item)
    except Exception:
        db.rollback()
        disk_path.unlink(missing_ok=True)
        raise
    background_tasks.add_task(run_snapshot_job, snapshot_id)
    return item


@router.get("", response_model=SnapshotPage)
def list_snapshots(
    camera_id: UUID | None = None,
    job_status: str | None = Query(default=None, pattern="^(queued|processing|completed|failed)$"),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _user: User = Depends(reader), db: Session = Depends(get_db),
):
    filters = []
    if camera_id is not None:
        filters.append(Snapshot.camera_id == camera_id)
    if job_status is not None:
        filters.append(Snapshot.job_status == job_status)
    if from_date is not None:
        if from_date.utcoffset() is None:
            raise APIError(422, "INVALID_DATE_FILTER", "from requires a timezone")
        from_date = from_date.astimezone(timezone.utc)
        filters.append(Snapshot.captured_at >= from_date)
    if to_date is not None:
        if to_date.utcoffset() is None:
            raise APIError(422, "INVALID_DATE_FILTER", "to requires a timezone")
        to_date = to_date.astimezone(timezone.utc)
        filters.append(Snapshot.captured_at <= to_date)
    if from_date and to_date and from_date > to_date:
        raise APIError(422, "INVALID_DATE_FILTER", "from must be <= to")
    total = db.scalar(select(func.count()).select_from(Snapshot).where(*filters)) or 0
    rows = db.scalars(select(Snapshot).where(*filters).order_by(
        Snapshot.captured_at.desc(), Snapshot.id.desc()).limit(limit).offset(offset)).all()
    return SnapshotPage(items=rows, total=total, limit=limit, offset=offset)


@router.get("/{snapshot_id}", response_model=SnapshotOut)
def get_snapshot(snapshot_id: UUID, _user: User = Depends(reader), db: Session = Depends(get_db)):
    item = db.get(Snapshot, snapshot_id)
    if item is None:
        raise APIError(404, "SNAPSHOT_NOT_FOUND", "Snapshot not found")
    preds = db.scalars(select(SpotPrediction).where(SpotPrediction.snapshot_id == snapshot_id)
                       .order_by(SpotPrediction.spot_code_at_capture)).all()
    result = [PredictionOut(
        id=p.id, parking_spot_id=p.parking_spot_id,
        spot_code=p.spot_code_at_capture, polygon=p.polygon_at_capture,
        predicted_label=p.predicted_label, effective_label=p.predicted_label,
        raw_label=p.raw_label, confidence=p.confidence, scores=p.scores,
        model_version=p.model_version, threshold=p.threshold,
    ) for p in preds]
    summary = summary_from_predictions(result) if item.job_status == "completed" else None
    stale_minutes = get_settings().stale_threshold_minutes
    # SQLite drops timezone offsets even for DateTime(timezone=True); PostgreSQL
    # keeps them. The API requires timezone-aware input and normalizes UTC.
    capture_time = item.captured_at
    if capture_time.tzinfo is None:
        capture_time = capture_time.replace(tzinfo=timezone.utc)
    # A failed/queued job is not automatically STALE. The dashboard should
    # separately track freshness of the latest completed snapshot per camera.
    is_stale = (datetime.now(timezone.utc) - capture_time > timedelta(minutes=stale_minutes)) \
        if item.job_status == "completed" else None
    return SnapshotOut(
        id=item.id, camera_id=item.camera_id, captured_at=capture_time,
        camera_config_version=item.camera_config_version, job_status=item.job_status,
        created_at=item.created_at, error_code=item.error_code,
        ai_model_version=item.ai_model_version, ai_threshold=item.ai_threshold,
        ai_processing_time_ms=item.ai_processing_time_ms, summary=summary,
        predictions=result, is_stale=is_stale,
    )


@router.get("/{snapshot_id}/image", response_class=FileResponse)
def get_snapshot_image(snapshot_id: UUID, _user: User = Depends(reader), db: Session = Depends(get_db)):
    item = db.get(Snapshot, snapshot_id)
    if item is None:
        raise APIError(404, "SNAPSHOT_NOT_FOUND", "Snapshot not found")
    try:
        path = locate_snapshot(snapshot_id, item.image_path)
    except (FileNotFoundError, ValueError):
        raise APIError(404, "SNAPSHOT_IMAGE_NOT_FOUND", "Snapshot image unavailable") from None
    return FileResponse(
        path, media_type="image/jpeg" if path.suffix == ".jpg" else "image/png",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
