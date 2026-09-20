"""add versioned non-authoritative Segment rubric shadow decisions

Revision ID: c8e2f4a6b913
Revises: b2c3d4e5f6a7
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "c8e2f4a6b913"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "segment_rubric_decision_shadows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("segment_review_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("rubric_version", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["segment_review_id"], ["segment_learning_reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ai_execution_id"], ["ai_executions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "segment_review_id", "policy_version", "provider", "model",
            name="uq_segment_rubric_shadow_identity",
        ),
        sa.CheckConstraint(
            "status IN ('COMPLETED', 'ABSTAINED', 'FAILED', 'NOT_APPLICABLE')",
            name="ck_segment_rubric_shadow_status",
        ),
    )
    op.create_index(
        "ix_segment_rubric_shadow_review",
        "segment_rubric_decision_shadows",
        ["segment_review_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_segment_rubric_shadow_review",
        table_name="segment_rubric_decision_shadows",
    )
    op.drop_table("segment_rubric_decision_shadows")
