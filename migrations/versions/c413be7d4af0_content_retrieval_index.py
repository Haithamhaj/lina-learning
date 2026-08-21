"""Add versioned PostgreSQL lexical and pgvector content index.

Revision ID: c413be7d4af0
Revises: b30c7a02f1e4
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "c413be7d4af0"
down_revision = "b30c7a02f1e4"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.drop_index("ix_content_blocks_embedding", table_name="content_blocks")
    op.drop_column("content_blocks", "embedding")
    op.create_table("content_index_runs", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("structural_processing_run_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("semantic_processing_run_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("block_schema_version", sa.String(128), nullable=False), sa.Column("embedding_route_version", sa.String(255), nullable=False), sa.Column("embedding_dimensions", sa.SmallInteger(), nullable=False), sa.Column("settings_version", sa.String(128), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"), sa.Column("failure_detail", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.ForeignKeyConstraint(["document_id"], ["content_documents.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["structural_processing_run_id"], ["content_processing_runs.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["semantic_processing_run_id"], ["content_semantic_processing_runs.id"], ondelete="CASCADE"), sa.UniqueConstraint("document_id", "semantic_processing_run_id", "block_schema_version", "embedding_route_version", "settings_version", name="uq_content_index_run_identity"))
    op.create_index("ix_content_index_runs_document_status", "content_index_runs", ["document_id", "status"])
    op.create_table("indexed_content_blocks", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("index_run_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("semantic_item_id", postgresql.UUID(as_uuid=True)), sa.Column("block_key", sa.String(512), nullable=False), sa.Column("block_type", sa.String(64), nullable=False), sa.Column("semantic_type", sa.String(32)), sa.Column("grade_level", sa.SmallInteger(), nullable=False), sa.Column("subject", sa.String(32), nullable=False), sa.Column("unit_key", sa.String(255)), sa.Column("lesson_key", sa.String(255)), sa.Column("concept_key", sa.String(255)), sa.Column("text", sa.Text(), nullable=False), sa.Column("search_vector", postgresql.TSVECTOR(), nullable=False), sa.Column("embedding", Vector(1536), nullable=False), sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"), sa.ForeignKeyConstraint(["index_run_id"], ["content_index_runs.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["document_id"], ["content_documents.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["semantic_item_id"], ["content_semantic_items.id"], ondelete="SET NULL"))
    op.create_index("ix_indexed_content_blocks_filter", "indexed_content_blocks", ["index_run_id", "grade_level", "subject", "unit_key", "lesson_key", "concept_key", "semantic_type"])
    op.create_index("ix_indexed_content_blocks_search", "indexed_content_blocks", ["search_vector"], postgresql_using="gin")
    op.create_index("ix_indexed_content_blocks_embedding", "indexed_content_blocks", ["embedding"], postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"})
    op.create_table("indexed_content_block_sources", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("block_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("semantic_item_id", postgresql.UUID(as_uuid=True)), sa.Column("structural_item_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("page_number", sa.SmallInteger()), sa.Column("source_ref", sa.String(512), nullable=False), sa.Column("source_order", sa.SmallInteger(), nullable=False), sa.ForeignKeyConstraint(["block_id"], ["indexed_content_blocks.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["semantic_item_id"], ["content_semantic_items.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["structural_item_id"], ["document_structural_items.id"], ondelete="CASCADE"), sa.UniqueConstraint("block_id", "structural_item_id", name="uq_indexed_content_block_source"))

def downgrade() -> None:
    op.drop_table("indexed_content_block_sources")
    op.drop_index("ix_indexed_content_blocks_embedding", table_name="indexed_content_blocks")
    op.drop_index("ix_indexed_content_blocks_search", table_name="indexed_content_blocks")
    op.drop_index("ix_indexed_content_blocks_filter", table_name="indexed_content_blocks")
    op.drop_table("indexed_content_blocks")
    op.drop_index("ix_content_index_runs_document_status", table_name="content_index_runs")
    op.drop_table("content_index_runs")
    op.add_column("content_blocks", sa.Column("embedding", Vector(8), nullable=True))
    op.create_index("ix_content_blocks_embedding", "content_blocks", ["embedding"], postgresql_using="hnsw", postgresql_ops={"embedding": "vector_l2_ops"})
