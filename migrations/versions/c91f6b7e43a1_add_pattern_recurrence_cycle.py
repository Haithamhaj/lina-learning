"""Separate recurrence cycles from preserved Pattern history.

Revision ID: c91f6b7e43a1
Revises: b82f4a65d982
"""

from alembic import op
import sqlalchemy as sa


revision = "c91f6b7e43a1"
down_revision = "b82f4a65d982"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learner_patterns",
        sa.Column("cycle_number", sa.SmallInteger(), nullable=False, server_default="1"),
    )
    op.add_column(
        "pattern_evidence",
        sa.Column("cycle_number", sa.SmallInteger(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("pattern_evidence", "cycle_number")
    op.drop_column("learner_patterns", "cycle_number")
