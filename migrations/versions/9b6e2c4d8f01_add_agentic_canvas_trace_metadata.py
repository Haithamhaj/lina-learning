"""Add bounded Agents SDK trace metadata to Canvas runs.

Revision ID: 9b6e2c4d8f01
Revises: 8f4d2a9c6b31
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "9b6e2c4d8f01"
down_revision = "8f4d2a9c6b31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "studio_canvas_specialist_runs",
        sa.Column("sdk_trace_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "studio_canvas_specialist_runs",
        sa.Column("agent_execution_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("studio_canvas_specialist_runs", "agent_execution_metadata")
    op.drop_column("studio_canvas_specialist_runs", "sdk_trace_id")
