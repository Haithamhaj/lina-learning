"""Persist durable typed Canvas Specialist proposal lineage.

Revision ID: d1c4a7e2b9f0
Revises: c7d8e9f0a1b2
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d1c4a7e2b9f0"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("studio_canvas_specialist_runs", sa.Column("order_digest", sa.String(length=64), nullable=True))
    op.add_column("studio_canvas_specialist_runs", sa.Column("proposal_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("studio_canvas_specialist_runs", sa.Column("proposal_digest", sa.String(length=64), nullable=True))
    op.create_index("uq_studio_specialist_runs_execution_identity", "studio_canvas_specialist_runs", ["source_message_id", "order_digest", "capability_profile_version"], unique=True, postgresql_where=sa.text("order_digest IS NOT NULL"))


def downgrade() -> None:
    op.drop_index("uq_studio_specialist_runs_execution_identity", table_name="studio_canvas_specialist_runs")
    op.drop_column("studio_canvas_specialist_runs", "proposal_digest")
    op.drop_column("studio_canvas_specialist_runs", "proposal_payload")
    op.drop_column("studio_canvas_specialist_runs", "order_digest")
