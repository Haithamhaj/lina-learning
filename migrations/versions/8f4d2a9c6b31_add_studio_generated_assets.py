"""Persist immutable, Student-owned generated Studio assets.

Revision ID: 8f4d2a9c6b31
Revises: a8c4d2e6f901
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "8f4d2a9c6b31"
down_revision = "a8c4d2e6f901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_studio_specialist_runs_id_runtime_student_session",
        "studio_canvas_specialist_runs",
        ["id", "studio_runtime_id", "student_id", "learning_session_id"],
    )
    op.create_table(
        "studio_generated_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learning_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("studio_runtime_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), server_default="IMAGE", nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("kind = 'IMAGE'", name="ck_studio_generated_assets_kind"),
        sa.CheckConstraint("size_bytes > 0", name="ck_studio_generated_assets_size_positive"),
        sa.CheckConstraint(
            "checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_studio_generated_assets_checksum_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["studio_runtime_id", "student_id", "learning_session_id"],
            ["studio_runtimes.id", "studio_runtimes.student_id", "studio_runtimes.learning_session_id"],
            name="fk_studio_generated_assets_runtime_student_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_run_id", "studio_runtime_id", "student_id", "learning_session_id"],
            [
                "studio_canvas_specialist_runs.id",
                "studio_canvas_specialist_runs.studio_runtime_id",
                "studio_canvas_specialist_runs.student_id",
                "studio_canvas_specialist_runs.learning_session_id",
            ],
            name="fk_studio_generated_assets_run_runtime_student_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_studio_generated_assets_storage_key"),
    )
    op.create_index(
        "ix_studio_generated_assets_student_runtime_created",
        "studio_generated_assets",
        ["student_id", "studio_runtime_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_studio_generated_assets_student_runtime_created",
        table_name="studio_generated_assets",
    )
    op.drop_table("studio_generated_assets")
    op.drop_constraint(
        "uq_studio_specialist_runs_id_runtime_student_session",
        "studio_canvas_specialist_runs",
        type_="unique",
    )
