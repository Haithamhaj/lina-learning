"""Add an independent clock and claim gate for worker pool lifecycle.

Revision ID: d9a4f1b6c203
Revises: c8e2f4a6b913
"""

import sqlalchemy as sa
from alembic import op

revision = "d9a4f1b6c203"
down_revision = "c8e2f4a6b913"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "worker_activity",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("last_user_activity_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "worker_lifecycle_state",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("stop_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("operation_name", sa.String(length=512), nullable=True),
        sa.Column("operation_target", sa.SmallInteger(), nullable=True),
    )
    op.execute("INSERT INTO worker_lifecycle_state (id, stop_requested) VALUES (1, false)")


def downgrade() -> None:
    op.drop_table("worker_lifecycle_state")
    op.drop_table("worker_activity")
