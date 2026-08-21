"""Persist versioned, source-linked Grade 5 Math semantic derivations.

Revision ID: b30c7a02f1e4
Revises: 1c32f331f02b
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b30c7a02f1e4"
down_revision = "1c32f331f02b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_semantic_processing_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("structural_processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("semantic_schema_version", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=128), nullable=False),
        sa.Column("model_route_version", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("settings_version", sa.String(length=128), nullable=False),
        sa.Column("settings_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["content_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["structural_processing_run_id"], ["content_processing_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "structural_processing_run_id", "semantic_schema_version", "prompt_version", "model_route_version", "settings_version", name="uq_content_semantic_processing_identity"),
    )
    op.create_index("ix_content_semantic_runs_document_status", "content_semantic_processing_runs", ["document_id", "status"])
    op.create_table(
        "content_semantic_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("semantic_processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("semantic_key", sa.String(length=255), nullable=False),
        sa.Column("semantic_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("normalized_concept_key", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sibling_order", sa.Integer(), nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.CheckConstraint("sibling_order >= 0", name="ck_content_semantic_item_sibling_order"),
        sa.ForeignKeyConstraint(["document_id"], ["content_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["semantic_processing_run_id"], ["content_semantic_processing_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["content_semantic_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("semantic_processing_run_id", "semantic_key", name="uq_content_semantic_item_key"),
    )
    op.create_index("ix_content_semantic_items_run_parent_order", "content_semantic_items", ["semantic_processing_run_id", "parent_id", "sibling_order"])
    op.create_index("ix_content_semantic_items_document_type", "content_semantic_items", ["document_id", "semantic_type"])
    op.create_table(
        "content_semantic_item_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("semantic_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("structural_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("structural_item_key", sa.String(length=512), nullable=False),
        sa.Column("page_number", sa.SmallInteger(), nullable=True),
        sa.Column("source_ref", sa.String(length=512), nullable=False),
        sa.Column("source_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("source_order >= 0", name="ck_content_semantic_item_source_order"),
        sa.ForeignKeyConstraint(["semantic_item_id"], ["content_semantic_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["structural_item_id"], ["document_structural_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("semantic_item_id", "structural_item_id", name="uq_content_semantic_item_source"),
    )
    op.create_index("ix_content_semantic_sources_structural", "content_semantic_item_sources", ["structural_item_id"])


def downgrade() -> None:
    op.drop_index("ix_content_semantic_sources_structural", table_name="content_semantic_item_sources")
    op.drop_table("content_semantic_item_sources")
    op.drop_index("ix_content_semantic_items_document_type", table_name="content_semantic_items")
    op.drop_index("ix_content_semantic_items_run_parent_order", table_name="content_semantic_items")
    op.drop_table("content_semantic_items")
    op.drop_index("ix_content_semantic_runs_document_status", table_name="content_semantic_processing_runs")
    op.drop_table("content_semantic_processing_runs")
