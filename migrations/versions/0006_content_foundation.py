"""Add versioned source content and provenance records.

Revision ID: 0006_content_foundation
Revises: 0005_safety_policy_foundation
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_content_foundation"
down_revision = "0005_safety_policy_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grade_level", sa.SmallInteger(), nullable=False),
        sa.Column("subject", sa.String(length=32), nullable=False),
        sa.Column("original_storage_key", sa.String(length=512), nullable=False),
        sa.Column("original_checksum", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="UPLOADED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("grade_level BETWEEN 1 AND 12", name="ck_content_document_grade"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "original_checksum", name="uq_content_document_checksum"),
    )
    op.create_table(
        "content_processing_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("processor_version", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["content_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_processing_document_kind", "content_processing_runs", ["document_id", "kind"])
    op.create_table(
        "curriculum_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("node_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(length=512), nullable=False),
        sa.Column("page_number", sa.SmallInteger(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["content_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_run_id"], ["content_processing_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["curriculum_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_curriculum_nodes_document_parent", "curriculum_nodes", ["document_id", "parent_id"])
    op.create_table(
        "content_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("curriculum_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("block_type", sa.String(length=32), nullable=False),
        sa.Column("page_number", sa.SmallInteger(), nullable=True),
        sa.Column("source_ref", sa.String(length=512), nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["document_id"], ["content_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_run_id"], ["content_processing_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["curriculum_node_id"], ["curriculum_nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_blocks_document_run", "content_blocks", ["document_id", "processing_run_id"])


def downgrade() -> None:
    op.drop_index("ix_content_blocks_document_run", table_name="content_blocks")
    op.drop_table("content_blocks")
    op.drop_index("ix_curriculum_nodes_document_parent", table_name="curriculum_nodes")
    op.drop_table("curriculum_nodes")
    op.drop_index("ix_content_processing_document_kind", table_name="content_processing_runs")
    op.drop_table("content_processing_runs")
    op.drop_table("content_documents")
