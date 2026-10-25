"""Initial 8-entity schema from backend W1 ERD.

Revision ID: 20261025_01
Revises:
Create Date: 2026-10-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261025_01"
down_revision = None
branch_labels = None
depends_on = None

UUID = sa.Uuid(as_uuid=True)
POLYGON_JSON = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("username", sa.String(80), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.CheckConstraint("role IN ('admin', 'operator')", name="ck_users_role"),
    )
    op.create_table(
        "parking_lots",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "cameras",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("parking_lot_id", UUID, sa.ForeignKey("parking_lots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("reference_image_path", sa.String(500)),
        sa.Column("reference_width", sa.Integer()),
        sa.Column("reference_height", sa.Integer()),
        sa.Column("config_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.CheckConstraint("config_version >= 1", name="ck_cameras_config_version"),
        sa.CheckConstraint("reference_width IS NULL OR reference_width > 0", name="ck_cameras_width"),
        sa.CheckConstraint("reference_height IS NULL OR reference_height > 0", name="ck_cameras_height"),
    )
    op.create_index("ix_cameras_parking_lot_id", "cameras", ["parking_lot_id"])
    op.create_table(
        "parking_spots",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("camera_id", UUID, sa.ForeignKey("cameras.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("spot_code", sa.String(40), nullable=False),
        sa.Column("polygon", POLYGON_JSON, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("camera_id", "spot_code", name="uq_parking_spots_camera_code"),
    )
    op.create_index("ix_parking_spots_camera_id", "parking_spots", ["camera_id"])
    op.create_table(
        "snapshots",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("camera_id", UUID, sa.ForeignKey("cameras.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("image_path", sa.String(500), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("camera_config_version", sa.Integer(), nullable=False),
        sa.Column("job_status", sa.String(20), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("error_code", sa.String(100)),
        sa.CheckConstraint("camera_config_version >= 1", name="ck_snapshots_config_version"),
        sa.CheckConstraint("job_status IN ('queued', 'processing', 'completed', 'failed')", name="ck_snapshots_job_status"),
    )
    op.create_index("ix_snapshots_camera_captured_at", "snapshots", ["camera_id", "captured_at"])
    op.create_table(
        "spot_predictions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("snapshot_id", UUID, sa.ForeignKey("snapshots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("parking_spot_id", UUID, sa.ForeignKey("parking_spots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("spot_code_at_capture", sa.String(40), nullable=False),
        sa.Column("polygon_at_capture", POLYGON_JSON, nullable=False),
        sa.Column("predicted_label", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.UniqueConstraint("snapshot_id", "parking_spot_id", name="uq_spot_predictions_snapshot_spot"),
        sa.CheckConstraint("predicted_label IN ('empty', 'occupied', 'unknown')", name="ck_spot_predictions_label"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_spot_predictions_confidence"),
    )
    op.create_index("ix_spot_predictions_snapshot_id", "spot_predictions", ["snapshot_id"])
    op.create_index("ix_spot_predictions_parking_spot_id", "spot_predictions", ["parking_spot_id"])
    op.create_table(
        "spot_reviews",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("spot_prediction_id", UUID, sa.ForeignKey("spot_predictions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reviewer_id", UUID, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("verified_label", sa.String(20), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(1000)),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("spot_prediction_id", "revision", name="uq_spot_reviews_prediction_revision"),
        sa.CheckConstraint("revision >= 1", name="ck_spot_reviews_revision"),
        sa.CheckConstraint("verified_label IN ('empty', 'occupied', 'unknown')", name="ck_spot_reviews_label"),
    )
    op.create_index("ix_spot_reviews_spot_prediction_id", "spot_reviews", ["spot_prediction_id"])
    op.create_index("ix_spot_reviews_reviewer_id", "spot_reviews", ["reviewer_id"])
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("actor_id", UUID, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", UUID, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("spot_reviews")
    op.drop_table("spot_predictions")
    op.drop_table("snapshots")
    op.drop_table("parking_spots")
    op.drop_table("cameras")
    op.drop_table("parking_lots")
    op.drop_table("users")
