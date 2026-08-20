"""Persist Docling structural trees separately from retrieval blocks.

Revision ID: 1c32f331f02b
Revises: f81d44c671b9
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "1c32f331f02b"
down_revision = "f81d44c671b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_processing_runs",
        sa.Column("processor_name", sa.String(length=64), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "content_processing_runs",
        sa.Column("library_version", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "content_processing_runs",
        sa.Column(
            "processor_settings_version",
            sa.String(length=128),
            nullable=False,
            server_default="legacy-unspecified",
        ),
    )
    op.add_column(
        "content_processing_runs",
        sa.Column(
            "processor_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.drop_constraint("uq_content_processing_run_version", "content_processing_runs", type_="unique")
    op.create_unique_constraint(
        "uq_content_processing_run_version",
        "content_processing_runs",
        ["document_id", "kind", "processor_version", "processor_settings_version"],
    )
    op.create_table(
        "document_structural_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("item_key", sa.String(length=512), nullable=False),
        sa.Column("sibling_order", sa.Integer(), nullable=False),
        sa.Column("reading_order", sa.Integer(), nullable=False),
        sa.Column("hierarchy_depth", sa.SmallInteger(), nullable=False),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("caption_text", sa.Text(), nullable=True),
        sa.Column("caption_item_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("heading_level", sa.SmallInteger(), nullable=True),
        sa.Column("page_number", sa.SmallInteger(), nullable=True),
        sa.Column("source_ref", sa.String(length=512), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.CheckConstraint("hierarchy_depth >= 0", name="ck_document_structural_item_hierarchy_depth"),
        sa.CheckConstraint("reading_order >= 0", name="ck_document_structural_item_reading_order"),
        sa.CheckConstraint("sibling_order >= 0", name="ck_document_structural_item_sibling_order"),
        sa.ForeignKeyConstraint(["document_id"], ["content_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["document_structural_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_run_id"], ["content_processing_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("processing_run_id", "item_key", name="uq_document_structural_item_key"),
    )
    op.create_index(
        "ix_document_structural_items_run_parent_order",
        "document_structural_items",
        ["processing_run_id", "parent_id", "sibling_order"],
    )
    op.create_index(
        "ix_document_structural_items_document_run_order",
        "document_structural_items",
        ["document_id", "processing_run_id", "reading_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_structural_items_document_run_order", table_name="document_structural_items")
    op.drop_index("ix_document_structural_items_run_parent_order", table_name="document_structural_items")
    op.drop_table("document_structural_items")
    op.drop_constraint("uq_content_processing_run_version", "content_processing_runs", type_="unique")
    op.create_unique_constraint(
        "uq_content_processing_run_version",
        "content_processing_runs",
        ["document_id", "kind", "processor_version"],
    )
    op.drop_column("content_processing_runs", "processor_metadata")
    op.drop_column("content_processing_runs", "processor_settings_version")
    op.drop_column("content_processing_runs", "library_version")
    op.drop_column("content_processing_runs", "processor_name")
