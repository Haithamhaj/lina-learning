"""Add identifier-only execution lineage to the existing AI ledger.

Revision ID: 9d92f905e25a
Revises: c51e8fa3b923
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "9d92f905e25a"
down_revision = "c51e8fa3b923"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_executions", sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_executions", sa.Column("operation_type", sa.String(length=64), nullable=True))
    op.add_column("ai_executions", sa.Column("parent_execution_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_executions", sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_executions", sa.Column("learning_session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_executions", sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_executions", sa.Column("intelligence_processing_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_executions", sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_executions", sa.Column("semantic_processing_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_executions", sa.Column("content_index_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_executions", sa.Column("source_candidate_event_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("learning_messages", sa.Column("ai_execution_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("candidate_events", sa.Column("ai_execution_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_ai_executions_parent_execution", "ai_executions", "ai_executions", ["parent_execution_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_ai_executions_student", "ai_executions", "students", ["student_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_ai_executions_session", "ai_executions", "learning_sessions", ["learning_session_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_ai_executions_source_message", "ai_executions", "learning_messages", ["source_message_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_ai_executions_intelligence_run", "ai_executions", "intelligence_processing_runs", ["intelligence_processing_run_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_ai_executions_document", "ai_executions", "content_documents", ["document_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_ai_executions_semantic_run", "ai_executions", "content_semantic_processing_runs", ["semantic_processing_run_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_ai_executions_index_run", "ai_executions", "content_index_runs", ["content_index_run_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_learning_messages_ai_execution", "learning_messages", "ai_executions", ["ai_execution_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_candidate_events_ai_execution", "candidate_events", "ai_executions", ["ai_execution_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_ai_executions_student_created", "ai_executions", ["student_id", "created_at"])
    op.create_index("ix_ai_executions_session_created", "ai_executions", ["learning_session_id", "created_at"])
    op.create_index("ix_ai_executions_operation", "ai_executions", ["operation_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_executions_operation", table_name="ai_executions")
    op.drop_index("ix_ai_executions_session_created", table_name="ai_executions")
    op.drop_index("ix_ai_executions_student_created", table_name="ai_executions")
    for name, table in (
        ("fk_candidate_events_ai_execution", "candidate_events"),
        ("fk_learning_messages_ai_execution", "learning_messages"),
        ("fk_ai_executions_index_run", "ai_executions"),
        ("fk_ai_executions_semantic_run", "ai_executions"),
        ("fk_ai_executions_document", "ai_executions"),
        ("fk_ai_executions_intelligence_run", "ai_executions"),
        ("fk_ai_executions_source_message", "ai_executions"),
        ("fk_ai_executions_session", "ai_executions"),
        ("fk_ai_executions_student", "ai_executions"),
        ("fk_ai_executions_parent_execution", "ai_executions"),
    ):
        op.drop_constraint(name, table, type_="foreignkey")
    op.drop_column("candidate_events", "ai_execution_id")
    op.drop_column("learning_messages", "ai_execution_id")
    for column in (
        "source_candidate_event_ids", "content_index_run_id", "semantic_processing_run_id",
        "document_id", "intelligence_processing_run_id", "source_message_id",
        "learning_session_id", "student_id", "parent_execution_id", "operation_type", "operation_id",
    ):
        op.drop_column("ai_executions", column)
