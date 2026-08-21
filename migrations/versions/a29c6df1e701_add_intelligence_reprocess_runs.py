"""add bounded intelligence reprocess run audit table

Revision ID: a29c6df1e701
Revises: f2d8c3a1b4e5
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a29c6df1e701"
down_revision = "f2d8c3a1b4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intelligence_reprocess_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("version_set", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("idempotency_key", name="uq_intelligence_reprocess_idempotency"),
    )
    op.create_index("ix_intelligence_reprocess_student_status", "intelligence_reprocess_runs", ["student_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_intelligence_reprocess_student_status", table_name="intelligence_reprocess_runs")
    op.drop_table("intelligence_reprocess_runs")
