"""Persist exact Canvas Specialist causal Scene identity.

Revision ID: e2f6a9c4d8b1
Revises: d1c4a7e2b9f0
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e2f6a9c4d8b1"
down_revision = "d1c4a7e2b9f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("studio_canvas_specialist_runs", sa.Column("base_scene_id", postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("studio_canvas_specialist_runs", "base_scene_id")
