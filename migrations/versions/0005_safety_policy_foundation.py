"""Add parent learning boundaries and policy audit records.

Revision ID: 0005_safety_policy_foundation
Revises: 0004_ai_execution_ledger
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_safety_policy_foundation"
down_revision = "0004_ai_execution_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_topic_boundaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("policy_version", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("state IN ('ALLOW', 'AGE_APPROPRIATE_ONLY', 'REDIRECT_TO_PARENT')", name="ck_student_topic_boundary_state"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "category", name="uq_student_topic_boundary"),
    )
    op.create_table(
        "safety_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interaction_ref", sa.String(length=128), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("policy_source", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_safety_audits_student_created", "safety_audits", ["student_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_safety_audits_student_created", table_name="safety_audits")
    op.drop_table("safety_audits")
    op.drop_table("student_topic_boundaries")
