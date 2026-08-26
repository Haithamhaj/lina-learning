"""Add durable session-local Segment identity and nullable message lineage.

Revision ID: f3a7d9c1e2b4
Revises: e6f7a8b9c0d1

Existing raw messages intentionally remain unsegmented.  Deleting a Segment
clears only its nullable lineage reference and never deletes raw messages.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f3a7d9c1e2b4"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


MESSAGE_SEGMENT_INDEX = "ix_learning_messages_session_segment_created_id"


def upgrade() -> None:
    op.create_table(
        "learning_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "sequence", name="uq_learning_segments_session_sequence"),
    )
    op.add_column(
        "learning_messages",
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_learning_messages_segment_id",
        "learning_messages",
        "learning_segments",
        ["segment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        MESSAGE_SEGMENT_INDEX,
        "learning_messages",
        ["session_id", "segment_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(MESSAGE_SEGMENT_INDEX, table_name="learning_messages")
    op.drop_constraint("fk_learning_messages_segment_id", "learning_messages", type_="foreignkey")
    op.drop_column("learning_messages", "segment_id")
    op.drop_table("learning_segments")
