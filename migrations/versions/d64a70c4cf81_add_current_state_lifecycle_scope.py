"""add current state lifecycle scope

Revision ID: d64a70c4cf81
Revises: c413be7d4af0
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "d64a70c4cf81"
down_revision = "c413be7d4af0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "current_learning_states",
        sa.Column("subject", sa.String(length=32), server_default="UNKNOWN", nullable=False),
    )
    op.add_column(
        "current_learning_states",
        sa.Column(
            "policy_version",
            sa.String(length=64),
            server_default="legacy-state-policy-v0",
            nullable=False,
        ),
    )
    op.add_column(
        "current_learning_states",
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "current_learning_states",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column("current_learning_states", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("current_learning_states", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_current_learning_states_student_subject_status",
        "current_learning_states",
        ["student_id", "subject", "status"],
        unique=False,
    )
    op.create_index("ix_current_learning_states_expiry", "current_learning_states", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_current_learning_states_expiry", table_name="current_learning_states")
    op.drop_index("ix_current_learning_states_student_subject_status", table_name="current_learning_states")
    op.drop_column("current_learning_states", "expires_at")
    op.drop_column("current_learning_states", "resolved_at")
    op.drop_column("current_learning_states", "updated_at")
    op.drop_column("current_learning_states", "detected_at")
    op.drop_column("current_learning_states", "policy_version")
    op.drop_column("current_learning_states", "subject")
