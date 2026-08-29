"""Add the persistence contract required by deterministic Session Finalization.

Revision ID: d7c3b9a5e1f2
Revises: e7b1f3c9a2d4

Historical Sessions remain on the legacy intelligence pipeline. The database
default applies the Segment Finalization pipeline only to newly inserted rows.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d7c3b9a5e1f2"
down_revision = "e7b1f3c9a2d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_sessions",
        sa.Column("intelligence_pipeline", sa.String(length=64), nullable=True),
    )
    op.execute(
        "UPDATE learning_sessions "
        "SET intelligence_pipeline = 'legacy-session-evidence-v1' "
        "WHERE intelligence_pipeline IS NULL"
    )
    op.alter_column(
        "learning_sessions",
        "intelligence_pipeline",
        existing_type=sa.String(length=64),
        nullable=False,
        server_default=sa.text("'segment-finalization-v1'"),
    )
    op.alter_column(
        "intelligence_session_authorities",
        "reprocess_run_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "learning_events",
        sa.Column("segment_review_finding_index", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_segment_finalization_session = connection.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM learning_sessions "
            "WHERE intelligence_pipeline = 'segment-finalization-v1'"
            ")"
        )
    ).scalar_one()
    if has_segment_finalization_session:
        raise RuntimeError(
            "Cannot downgrade while segment-finalization-v1 Sessions exist because "
            "a later upgrade would relabel them as legacy."
        )

    op.drop_column("learning_events", "segment_review_finding_index")
    op.alter_column(
        "intelligence_session_authorities",
        "reprocess_run_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("learning_sessions", "intelligence_pipeline")
