"""Add retrieval-only Learning Intelligence semantic projections.

Revision ID: fa1b2c3d4e5f
Revises: c51e8fa3b923
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "fa1b2c3d4e5f"
down_revision = "c51e8fa3b923"
branch_labels = None
depends_on = None


def _projection_table(name: str, source_column: str, source_table: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(source_column, sa.UUID(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("embedding_provider", sa.String(length=128), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("dimensions", sa.SmallInteger(), server_default="1536", nullable=False),
        sa.Column("representation_version", sa.String(length=128), nullable=False),
        sa.Column("representation_hash", sa.String(length=64), nullable=False),
        sa.Column("ai_execution_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint([source_column], [f"{source_table}.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ai_execution_id"], ["ai_executions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(source_column, "representation_version", "embedding_provider", "embedding_model", "dimensions", name=f"uq_{name}_route"),
    )
    op.create_index(f"ix_{name}_route", name, ["embedding_provider", "embedding_model", "dimensions"], unique=False)


def upgrade() -> None:
    _projection_table("current_learning_state_projections", "current_learning_state_id", "current_learning_states")
    _projection_table("learner_pattern_projections", "learner_pattern_id", "learner_patterns")


def downgrade() -> None:
    op.drop_index("ix_learner_pattern_projections_route", table_name="learner_pattern_projections")
    op.drop_table("learner_pattern_projections")
    op.drop_index("ix_current_learning_state_projections_route", table_name="current_learning_state_projections")
    op.drop_table("current_learning_state_projections")
