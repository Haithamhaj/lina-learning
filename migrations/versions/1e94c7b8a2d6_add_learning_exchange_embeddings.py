"""Add temporary session-scoped complete-exchange embedding storage.

Revision ID: 1e94c7b8a2d6
Revises: a4d8e2f6b1c3
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "1e94c7b8a2d6"
down_revision = "a4d8e2f6b1c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_exchange_embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("segment_id", sa.UUID(), nullable=False),
        sa.Column("student_message_id", sa.UUID(), nullable=False),
        sa.Column("tutor_message_id", sa.UUID(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("dimensions", sa.SmallInteger(), server_default="1536", nullable=False),
        sa.Column("ai_execution_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ai_execution_id"], ["ai_executions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["segment_id"], ["learning_segments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_message_id"], ["learning_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tutor_message_id"], ["learning_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_message_id",
            "tutor_message_id",
            "embedding_model",
            name="uq_learning_exchange_embedding_exchange_model",
        ),
    )
    op.create_index(
        "ix_learning_exchange_embeddings_session_segment",
        "learning_exchange_embeddings",
        ["session_id", "segment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_learning_exchange_embeddings_session_segment", table_name="learning_exchange_embeddings")
    op.drop_table("learning_exchange_embeddings")
