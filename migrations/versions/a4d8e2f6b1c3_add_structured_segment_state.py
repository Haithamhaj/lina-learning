"""Persist the replaceable latest CTX-03B Structured Segment State.

Revision ID: a4d8e2f6b1c3
Revises: f3a7d9c1e2b4

Raw LearningMessages remain the rebuildable source authority.  This nullable
JSONB projection intentionally has no history table and may be empty.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a4d8e2f6b1c3"
down_revision = "f3a7d9c1e2b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_segments",
        sa.Column("structured_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("learning_segments", "structured_state")
