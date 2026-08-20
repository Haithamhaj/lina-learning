"""Add the AI execution ledger.

Revision ID: 0004_ai_execution_ledger
Revises: 0003_jobs_worker_foundation
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_ai_execution_ledger"
down_revision = "0003_jobs_worker_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("input_tokens", sa.SmallInteger(), nullable=True),
        sa.Column("output_tokens", sa.SmallInteger(), nullable=True),
        sa.Column("latency_ms", sa.SmallInteger(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_executions_task_created", "ai_executions", ["task", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_executions_task_created", table_name="ai_executions")
    op.drop_table("ai_executions")
