"""Add immutable Student source assets and Tutor lineage.

Revision ID: a8c4d2e6f901
Revises: e2f6a9c4d8b1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a8c4d2e6f901"
down_revision = "e2f6a9c4d8b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_source_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learning_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("kind IN ('IMAGE', 'PDF', 'DOCUMENT')", name="ck_student_source_assets_kind"),
        sa.ForeignKeyConstraint(
            ["learning_session_id", "student_id"],
            ["learning_sessions.id", "learning_sessions.student_id"],
            name="fk_student_source_assets_session_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id", "learning_session_id"],
            ["learning_messages.id", "learning_messages.session_id"],
            name="fk_student_source_assets_message_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_message_id", name="uq_student_source_assets_source_message"),
        sa.UniqueConstraint("storage_key", name="uq_student_source_assets_storage_key"),
    )
    op.create_index(
        "ix_student_source_assets_student_session_created",
        "student_source_assets",
        ["student_id", "learning_session_id", "created_at"],
        unique=False,
    )
    op.add_column("learning_messages", sa.Column("source_asset_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_learning_messages_source_asset",
        "learning_messages",
        "student_source_assets",
        ["source_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_learning_messages_source_asset", "learning_messages", ["source_asset_id"], unique=False)
    op.add_column("ai_executions", sa.Column("source_asset_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_ai_executions_source_asset",
        "ai_executions",
        "student_source_assets",
        ["source_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_ai_executions_source_asset", "ai_executions", ["source_asset_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_executions_source_asset", table_name="ai_executions", if_exists=True)
    op.drop_constraint("fk_ai_executions_source_asset", "ai_executions", type_="foreignkey")
    op.drop_column("ai_executions", "source_asset_id")
    op.drop_index("ix_learning_messages_source_asset", table_name="learning_messages", if_exists=True)
    op.drop_constraint("fk_learning_messages_source_asset", "learning_messages", type_="foreignkey")
    op.drop_column("learning_messages", "source_asset_id")
    op.drop_index("ix_student_source_assets_student_session_created", table_name="student_source_assets")
    op.drop_table("student_source_assets")
