
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.errors import APIError
from app.db.session import get_db
from app.models import (
    AuditLog,
    Snapshot,
    SpotPrediction,
    SpotReview,
    User,
)
from app.schemas.reviews import ReviewCreate, ReviewOut

router = APIRouter(tags=["reviews"])
reviewer = require_roles("admin", "operator")


@router.post(
    "/predictions/{prediction_id}/reviews",
    response_model=ReviewOut,
    status_code=201,
)
def create_review(
    prediction_id: UUID,
    payload: ReviewCreate,
    user: User = Depends(reviewer),
    db: Session = Depends(get_db),
):
    # Lock prediction to serialize concurrent reviews.
    prediction = db.scalar(
        select(SpotPrediction)
        .where(SpotPrediction.id == prediction_id)
        .with_for_update()
    )

    if prediction is None:
        raise APIError(
            404, "PREDICTION_NOT_FOUND",
            "Prediction not found",
        )

    snapshot = db.get(Snapshot, prediction.snapshot_id)
    if snapshot is None or snapshot.job_status != "completed":
        raise APIError(
            409, "SNAPSHOT_NOT_COMPLETED",
            "Snapshot must be completed before review",
        )

    latest_revision = db.scalar(
        select(func.max(SpotReview.revision))
        .where(SpotReview.spot_prediction_id == prediction_id)
    ) or 0

    if payload.expected_revision != latest_revision:
        raise APIError(
            409, "REVIEW_VERSION_CONFLICT",
            "Review changed; reload before submitting",
        )

    if payload.action == "accept":
        verified_label = prediction.predicted_label
    else:
        verified_label = payload.verified_label
        if verified_label == prediction.predicted_label:
            raise APIError(
                422, "UNCHANGED_LABEL",
                "Use accept when the AI label is correct",
            )

    review = SpotReview(
        spot_prediction_id=prediction_id,
        reviewer_id=user.id,
        verified_label=verified_label,
        revision=latest_revision + 1,
        reason=payload.reason,
    )

    db.add(review)

    try:
        db.flush()

        db.add(AuditLog(
            actor_id=user.id,
            action=f"prediction.review.{payload.action}",
            entity_type="spot_review",
            entity_id=review.id,
        ))

        db.commit()
    except IntegrityError:
        db.rollback()
        raise APIError(
            409, "REVIEW_VERSION_CONFLICT",
            "Concurrent review detected",
        ) from None

    db.refresh(review)

    return ReviewOut(
        id=review.id,
        prediction_id=prediction_id,
        reviewer_id=review.reviewer_id,
        action=payload.action,
        verified_label=review.verified_label,
        revision=review.revision,
        reason=review.reason,
        changed_at=review.changed_at,
    )
