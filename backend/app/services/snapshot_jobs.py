"""In-process async snapshot worker for local MVP.

BackgroundTasks are not durable if the process stops. For production use a real
queue and restart/reconciliation, keeping one stable snapshot ID per job.
"""
import logging
from uuid import UUID
from sqlalchemy import select

from app.db.session import get_session_factory
from app.models import Snapshot, SpotPrediction
from app.services.ai_client import AIJobError, infer
from app.services.snapshot_storage import load_snapshot

logger = logging.getLogger(__name__)


def run_snapshot_job(snapshot_id: UUID) -> None:
    factory = get_session_factory()
    try:
        with factory() as db:
            item = db.get(Snapshot, snapshot_id)
            if item is None or item.job_status != "queued":
                return
            item.job_status = "processing"
            db.commit()
            camera_id, key, spots = str(item.camera_id), item.image_path, item.spots_at_capture
        if not spots:
            raise AIJobError("INVALID_SNAPSHOT_SPOTS")
        image, mime = load_snapshot(snapshot_id, key)
        output = infer(camera_id, spots, image, mime)
        # Atomic commit: either all predictions and a completed status, or none.
        with factory() as db:
            item = db.get(Snapshot, snapshot_id)
            if item is None or item.job_status != "processing":
                return
            db.add_all([
                SpotPrediction(
                    snapshot_id=snapshot_id,
                    parking_spot_id=UUID(spot["id"]),
                    spot_code_at_capture=spot["spot_code"],
                    polygon_at_capture=spot["polygon"],
                    predicted_label=pred.label,
                    confidence=pred.confidence,
                    model_version=output.model_version,
                    raw_label=pred.raw_label,
                    scores=pred.scores,
                    threshold=output.threshold,
                )
                for spot, pred in zip(spots, output.predictions, strict=True)
            ])
            item.job_status = "completed"
            item.ai_model_version = output.model_version
            item.ai_threshold = output.threshold
            item.ai_processing_time_ms = output.processing_time_ms
            db.commit()
    except Exception as exc:
        code = exc.code if isinstance(exc, AIJobError) else "SNAPSHOT_PROCESSING_ERROR"
        if not isinstance(exc, AIJobError):
            logger.exception("Snapshot job failed: snapshot_id=%s", snapshot_id)
        with factory() as db:
            item = db.get(Snapshot, snapshot_id)
            if item is not None and item.job_status in ("queued", "processing"):
                item.job_status = "failed"
                item.error_code = code
                db.commit()
