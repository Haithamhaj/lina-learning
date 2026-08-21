"""add reprocess session results and explicit authority

Revision ID: b40d7ea2f812
Revises: a29c6df1e701
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b40d7ea2f812"
down_revision = "a29c6df1e701"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intelligence_reprocess_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reprocess_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_processing_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["reprocess_run_id"], ["intelligence_reprocess_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_processing_run_id"], ["intelligence_processing_runs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("reprocess_run_id", "session_id", name="uq_intelligence_reprocess_session"),
    )
    op.create_table(
        "intelligence_session_authorities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reprocess_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reprocess_run_id"], ["intelligence_reprocess_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_processing_run_id"], ["intelligence_processing_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("student_id", "session_id", name="uq_intelligence_session_authority"),
    )


def downgrade() -> None:
    op.drop_table("intelligence_session_authorities")
    op.drop_table("intelligence_reprocess_sessions")
