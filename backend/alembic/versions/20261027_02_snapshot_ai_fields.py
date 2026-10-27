"""W4: freeze camera spot configuration and retain detailed AI output.

Revision ID: 20261027_02
Revises: 20261025_01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261027_02"
down_revision = "20261025_01"
branch_labels = None
depends_on = None
JSONCOL = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    # Nullable fields preserve existing historical rows if this migration runs after W3.
    op.add_column("snapshots", sa.Column("spots_at_capture", JSONCOL, nullable=True))
    op.add_column("snapshots", sa.Column("ai_model_version", sa.String(100), nullable=True))
    op.add_column("snapshots", sa.Column("ai_threshold", sa.Float(), nullable=True))
    op.add_column("snapshots", sa.Column("ai_processing_time_ms", sa.Float(), nullable=True))
    op.add_column("spot_predictions", sa.Column("raw_label", sa.String(20), nullable=True))
    op.add_column("spot_predictions", sa.Column("scores", JSONCOL, nullable=True))
    op.add_column("spot_predictions", sa.Column("threshold", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("spot_predictions", "threshold")
    op.drop_column("spot_predictions", "scores")
    op.drop_column("spot_predictions", "raw_label")
    op.drop_column("snapshots", "ai_processing_time_ms")
    op.drop_column("snapshots", "ai_threshold")
    op.drop_column("snapshots", "ai_model_version")
    op.drop_column("snapshots", "spots_at_capture")
