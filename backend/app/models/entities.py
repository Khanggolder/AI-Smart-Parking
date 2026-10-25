"""Eight baseline ORM entities from docs/design/backend-architecture-erd.md.

Business-level polygon geometry and authorization checks will be implemented
in later W2/W3 services. These constraints enforce only DB-level invariants.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# JSONB on PostgreSQL; generic JSON in SQLite-based schema tests.
PolygonJSON = JSON().with_variant(JSONB(), "postgresql")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'operator')", name="ck_users_role"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class ParkingLot(Base):
    __tablename__ = "parking_lots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Camera(Base):
    __tablename__ = "cameras"
    __table_args__ = (
        CheckConstraint("config_version >= 1", name="ck_cameras_config_version"),
        CheckConstraint("reference_width IS NULL OR reference_width > 0", name="ck_cameras_width"),
        CheckConstraint("reference_height IS NULL OR reference_height > 0", name="ck_cameras_height"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parking_lot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("parking_lots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    reference_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    config_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class ParkingSpot(Base):
    __tablename__ = "parking_spots"
    __table_args__ = (UniqueConstraint("camera_id", "spot_code", name="uq_parking_spots_camera_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("cameras.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    spot_code: Mapped[str] = mapped_column(String(40), nullable=False)
    polygon: Mapped[list[dict[str, float]]] = mapped_column(PolygonJSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (
        CheckConstraint("camera_config_version >= 1", name="ck_snapshots_config_version"),
        CheckConstraint(
            "job_status IN ('queued', 'processing', 'completed', 'failed')",
            name="ck_snapshots_job_status",
        ),
        Index("ix_snapshots_camera_captured_at", "camera_id", "captured_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("cameras.id", ondelete="RESTRICT"), nullable=False
    )
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    camera_config_version: Mapped[int] = mapped_column(Integer, nullable=False)
    job_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'queued'"))
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)


class SpotPrediction(Base):
    __tablename__ = "spot_predictions"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "parking_spot_id", name="uq_spot_predictions_snapshot_spot"),
        CheckConstraint(
            "predicted_label IN ('empty', 'occupied', 'unknown')",
            name="ck_spot_predictions_label",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_spot_predictions_confidence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("snapshots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    parking_spot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("parking_spots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    spot_code_at_capture: Mapped[str] = mapped_column(String(40), nullable=False)
    polygon_at_capture: Mapped[list[dict[str, float]]] = mapped_column(PolygonJSON, nullable=False)
    predicted_label: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)


class SpotReview(Base):
    __tablename__ = "spot_reviews"
    __table_args__ = (
        UniqueConstraint("spot_prediction_id", "revision", name="uq_spot_reviews_prediction_revision"),
        CheckConstraint("revision >= 1", name="ck_spot_reviews_revision"),
        CheckConstraint("verified_label IN ('empty', 'occupied', 'unknown')", name="ck_spot_reviews_label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spot_prediction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("spot_predictions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    verified_label: Mapped[str] = mapped_column(String(20), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
