"""Foundational SQLAlchemy models.

Authentication, authorization roles, learning data, and content models belong
to later tasks. These models only establish durable identity and grade-period
relationships needed by the Phase 0 database foundation.
"""

from datetime import UTC, date, datetime
from enum import Enum
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base metadata for the Lina modular monolith."""


class JobStatus(str, Enum):
    """Durable lifecycle states for background work."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ModelTask(str, Enum):
    """Stable names for application-owned model requests."""

    TUTOR = "tutor"
    SESSION_EVIDENCE = "session_evidence"
    SEGMENT_EVIDENCE = "segment_evidence"
    CURRICULUM_SEMANTICS = "curriculum_semantics"
    EMBEDDING = "embedding"


class Job(Base):
    """Database-backed work item claimed by an independent worker process."""

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("attempt_count >= 0", name="ck_jobs_attempt_count_nonnegative"),
        CheckConstraint("max_attempts > 0", name="ck_jobs_max_attempts_positive"),
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_jobs_status",
        ),
        Index(
            "uq_jobs_type_idempotency_key",
            "job_type",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        Index("ix_jobs_claimable", "status", "run_after"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    job_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=JobStatus.PENDING.value,
        server_default=JobStatus.PENDING.value,
    )
    attempt_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    max_attempts: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=3,
        server_default="3",
    )
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    claimed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_token: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AIExecution(Base):
    """Immutable operational record for one Model Gateway request and its safe lineage."""

    __tablename__ = "ai_executions"
    __table_args__ = (
        Index("ix_ai_executions_task_created", "task", "created_at"),
        Index("ix_ai_executions_student_created", "student_id", "created_at"),
        Index("ix_ai_executions_session_created", "learning_session_id", "created_at"),
        Index("ix_ai_executions_operation", "operation_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    task: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    # Normal (non-cached) input tokens and cached input tokens are kept apart
    # so ledger cost estimates can be audited against provider usage.
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cache_write_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost_usd: Mapped[float | None] = mapped_column(nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # ``operation_id`` groups attempts for one application-owned logical action.
    # It deliberately stores identifiers only, never prompt, response, or vector data.
    operation_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    operation_type: Mapped[str | None] = mapped_column(String(64))
    parent_execution_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("ai_executions.id", ondelete="SET NULL"),
    )
    student_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="SET NULL")
    )
    learning_session_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="SET NULL")
    )
    source_message_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("learning_messages.id", ondelete="SET NULL")
    )
    intelligence_processing_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("intelligence_processing_runs.id", ondelete="SET NULL"),
    )
    document_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("content_documents.id", ondelete="SET NULL")
    )
    semantic_processing_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("content_semantic_processing_runs.id", ondelete="SET NULL"),
    )
    content_index_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("content_index_runs.id", ondelete="SET NULL"),
    )
    source_candidate_event_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StudentTopicBoundary(Base):
    """A Parent-controlled restriction for one configurable topic category."""

    __tablename__ = "student_topic_boundaries"
    __table_args__ = (
        UniqueConstraint("student_id", "category", name="uq_student_topic_boundary"),
        CheckConstraint(
            "state IN ('ALLOW', 'AGE_APPROPRIATE_ONLY', 'REDIRECT_TO_PARENT')",
            name="ck_student_topic_boundary_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    student_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_version: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default="1"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SafetyAudit(Base):
    """A compact, non-content policy decision audit record."""

    __tablename__ = "safety_audits"
    __table_args__ = (Index("ix_safety_audits_student_created", "student_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    student_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    interaction_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_source: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ContentDocument(Base):
    """Immutable source document registered for one student's active Grade."""

    __tablename__ = "content_documents"
    __table_args__ = (
        UniqueConstraint("student_id", "original_checksum", name="uq_content_document_checksum"),
        CheckConstraint("grade_level BETWEEN 1 AND 12", name="ck_content_document_grade"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    grade_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    original_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UPLOADED", server_default="UPLOADED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ContentProcessingRun(Base):
    """Versioned structural or semantic derivation from an immutable original."""

    __tablename__ = "content_processing_runs"
    __table_args__ = (
        Index("ix_content_processing_document_kind", "document_id", "kind"),
        UniqueConstraint(
            "document_id",
            "kind",
            "processor_version",
            "processor_settings_version",
            name="uq_content_processing_run_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_documents.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    processor_name: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown", server_default="unknown")
    processor_version: Mapped[str] = mapped_column(String(128), nullable=False)
    library_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    processor_settings_version: Mapped[str] = mapped_column(String(128), nullable=False, default="legacy-unspecified", server_default="legacy-unspecified")
    processor_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", server_default="PENDING")
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentStructuralItem(Base):
    """A project-owned node from one versioned document structural run.

    TASK-011 stores hierarchy explicitly here.  `ContentBlock` remains a
    later TASK-013 retrieval projection rather than the structural source.
    """

    __tablename__ = "document_structural_items"
    __table_args__ = (
        UniqueConstraint("processing_run_id", "item_key", name="uq_document_structural_item_key"),
        CheckConstraint("sibling_order >= 0", name="ck_document_structural_item_sibling_order"),
        CheckConstraint("reading_order >= 0", name="ck_document_structural_item_reading_order"),
        CheckConstraint("hierarchy_depth >= 0", name="ck_document_structural_item_hierarchy_depth"),
        Index("ix_document_structural_items_run_parent_order", "processing_run_id", "parent_id", "sibling_order"),
        Index("ix_document_structural_items_document_run_order", "document_id", "processing_run_id", "reading_order"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_documents.id", ondelete="CASCADE"), nullable=False)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_processing_runs.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("document_structural_items.id", ondelete="CASCADE"), nullable=True)
    item_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sibling_order: Mapped[int] = mapped_column(nullable=False)
    reading_order: Mapped[int] = mapped_column(nullable=False)
    hierarchy_depth: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_item_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    heading_level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    page_number: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    source_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")


class ContentSemanticProcessingRun(Base):
    """One versioned Grade 5 Math semantic derivation of a structural run."""

    __tablename__ = "content_semantic_processing_runs"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "structural_processing_run_id",
            "semantic_schema_version",
            "prompt_version",
            "model_route_version",
            "settings_version",
            name="uq_content_semantic_processing_identity",
        ),
        Index("ix_content_semantic_runs_document_status", "document_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_documents.id", ondelete="CASCADE"), nullable=False)
    structural_processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_processing_runs.id", ondelete="CASCADE"), nullable=False)
    semantic_schema_version: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(128), nullable=False)
    model_route_version: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    settings_version: Mapped[str] = mapped_column(String(128), nullable=False)
    settings_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", server_default="PENDING")
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ContentSemanticItem(Base):
    """A project-owned educational meaning with explicit source-item lineage."""

    __tablename__ = "content_semantic_items"
    __table_args__ = (
        UniqueConstraint("semantic_processing_run_id", "semantic_key", name="uq_content_semantic_item_key"),
        CheckConstraint("sibling_order >= 0", name="ck_content_semantic_item_sibling_order"),
        Index("ix_content_semantic_items_run_parent_order", "semantic_processing_run_id", "parent_id", "sibling_order"),
        Index("ix_content_semantic_items_document_type", "document_id", "semantic_type"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_documents.id", ondelete="CASCADE"), nullable=False)
    semantic_processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_semantic_processing_runs.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_semantic_items.id", ondelete="CASCADE"), nullable=True)
    semantic_key: Mapped[str] = mapped_column(String(255), nullable=False)
    semantic_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_concept_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sibling_order: Mapped[int] = mapped_column(nullable=False)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")


class ContentSemanticItemSource(Base):
    """Denormalized source/page reference for one semantic-to-structural link."""

    __tablename__ = "content_semantic_item_sources"
    __table_args__ = (
        UniqueConstraint("semantic_item_id", "structural_item_id", name="uq_content_semantic_item_source"),
        CheckConstraint("source_order >= 0", name="ck_content_semantic_item_source_order"),
        Index("ix_content_semantic_sources_structural", "structural_item_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    semantic_item_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_semantic_items.id", ondelete="CASCADE"), nullable=False)
    structural_item_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("document_structural_items.id", ondelete="CASCADE"), nullable=False)
    structural_item_key: Mapped[str] = mapped_column(String(512), nullable=False)
    page_number: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    source_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    source_order: Mapped[int] = mapped_column(nullable=False)


class CurriculumNode(Base):
    """Legacy curriculum projection retained for pre-remediation demo data.

    TASK-012 semantic truth now resides in ``ContentSemanticItem`` and its
    versioned source links; this table is not overwritten by new extraction.
    """

    __tablename__ = "curriculum_nodes"
    __table_args__ = (Index("ix_curriculum_nodes_document_parent", "document_id", "parent_id"),)

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_documents.id", ondelete="CASCADE"), nullable=False)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_processing_runs.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("curriculum_nodes.id", ondelete="CASCADE"), nullable=True)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    page_number: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)


class ContentBlock(Base):
    """Legacy pre-remediation content projection; not TASK-013 index truth."""

    __tablename__ = "content_blocks"
    __table_args__ = (
        Index("ix_content_blocks_document_run", "document_id", "processing_run_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_documents.id", ondelete="CASCADE"), nullable=False)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_processing_runs.id", ondelete="CASCADE"), nullable=False)
    curriculum_node_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("curriculum_nodes.id", ondelete="SET NULL"), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    block_type: Mapped[str] = mapped_column(String(32), nullable=False)
    page_number: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    source_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")


class ContentIndexRun(Base):
    """Versioned retrieval-index derivation from structural content and optional semantics."""

    __tablename__ = "content_index_runs"
    __table_args__ = (
        UniqueConstraint("document_id", "semantic_processing_run_id", "block_schema_version", "embedding_route_version", "settings_version", name="uq_content_index_run_identity"),
        Index(
            "uq_content_index_run_structural_identity",
            "document_id",
            "structural_processing_run_id",
            "block_schema_version",
            "embedding_route_version",
            "settings_version",
            unique=True,
            postgresql_where=text("semantic_processing_run_id IS NULL"),
        ),
        Index("ix_content_index_runs_document_status", "document_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_documents.id", ondelete="CASCADE"), nullable=False)
    structural_processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_processing_runs.id", ondelete="CASCADE"), nullable=False)
    semantic_processing_run_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_semantic_processing_runs.id", ondelete="CASCADE"), nullable=True)
    block_schema_version: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_route_version: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    settings_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", server_default="PENDING")
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IndexedContentBlock(Base):
    """A queryable semantic/structural retrieval block with DB-owned indexes."""

    __tablename__ = "indexed_content_blocks"
    __table_args__ = (
        Index("ix_indexed_content_blocks_filter", "index_run_id", "grade_level", "subject", "unit_key", "lesson_key", "concept_key", "semantic_type"),
        Index("ix_indexed_content_blocks_search", "search_vector", postgresql_using="gin"),
        Index("ix_indexed_content_blocks_embedding", "embedding", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    index_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_index_runs.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_documents.id", ondelete="CASCADE"), nullable=False)
    semantic_item_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_semantic_items.id", ondelete="SET NULL"))
    block_key: Mapped[str] = mapped_column(String(512), nullable=False)
    block_type: Mapped[str] = mapped_column(String(64), nullable=False)
    semantic_type: Mapped[str | None] = mapped_column(String(32))
    grade_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_key: Mapped[str | None] = mapped_column(String(255))
    lesson_key: Mapped[str | None] = mapped_column(String(255))
    concept_key: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    search_vector: Mapped[object] = mapped_column(TSVECTOR, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")


class IndexedContentBlockSource(Base):
    """Per-block structural and semantic provenance used by later retrieval."""

    __tablename__ = "indexed_content_block_sources"
    __table_args__ = (UniqueConstraint("block_id", "structural_item_id", name="uq_indexed_content_block_source"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    block_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("indexed_content_blocks.id", ondelete="CASCADE"), nullable=False)
    semantic_item_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_semantic_items.id", ondelete="SET NULL"))
    structural_item_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("document_structural_items.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int | None] = mapped_column(SmallInteger)
    source_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    source_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class LearningSession(Base):
    """Raw-session envelope; downstream intelligence remains derived."""

    __tablename__ = "learning_sessions"
    __table_args__ = (Index("ix_learning_sessions_student_status", "student_id", "status"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str] = mapped_column(String(32), nullable=False, default="MATH", server_default="MATH")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN", server_default="OPEN")
    intelligence_pipeline: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="segment-finalization-v1",
        server_default="segment-finalization-v1",
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LearningSegment(Base):
    """Contiguous session-local conversation segment; raw messages remain authoritative."""

    __tablename__ = "learning_segments"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_learning_segments_session_sequence"),
        CheckConstraint(
            "(closed_at IS NULL AND closure_reason IS NULL) OR "
            "(closed_at IS NOT NULL AND closure_reason IS NOT NULL AND "
            "closure_reason IN ('NEXT_SEGMENT_CREATED', 'SESSION_CLOSED'))",
            name="ck_learning_segments_closure_state",
        ),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    structured_state: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closure_reason: Mapped[str | None] = mapped_column(String(32))


class SegmentLearningReview(Base):
    """Versioned semantic-review artifact; raw messages remain source authority."""

    __tablename__ = "segment_learning_reviews"
    __table_args__ = (
        UniqueConstraint(
            "segment_id",
            "schema_version",
            "prompt_version",
            "rubric_version",
            "review_policy_version",
            "provider",
            "model",
            name="uq_segment_learning_review_identity",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_segment_learning_reviews_status",
        ),
        Index("ix_segment_learning_reviews_session", "session_id"),
        Index("ix_segment_learning_reviews_student", "student_id"),
        Index("ix_segment_learning_reviews_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    segment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("learning_segments.id", ondelete="RESTRICT"), nullable=False
    )
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(128), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(64), nullable=False)
    review_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING", server_default="PENDING")
    output: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    ai_execution_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("ai_executions.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_detail: Mapped[str | None] = mapped_column(Text)


class LearningMessage(Base):
    __tablename__ = "learning_messages"
    __table_args__ = (
        Index("ix_learning_messages_session_created", "session_id", "created_at"),
        Index(
            "ix_learning_messages_session_segment_created_id",
            "session_id",
            "segment_id",
            "created_at",
            "id",
        ),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False)
    segment_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("learning_segments.id", ondelete="SET NULL"),
        nullable=True,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
    ai_execution_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("ai_executions.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LearningExchangeEmbedding(Base):
    """Temporary vector index for one completed, source-authoritative exchange."""

    __tablename__ = "learning_exchange_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "student_message_id",
            "tutor_message_id",
            "embedding_model",
            name="uq_learning_exchange_embedding_exchange_model",
        ),
        Index("ix_learning_exchange_embeddings_session_segment", "session_id", "segment_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    segment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("learning_segments.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_message_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("learning_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    tutor_message_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("learning_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    dimensions: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1536, server_default="1536")
    ai_execution_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("ai_executions.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CandidateEvent(Base):
    __tablename__ = "candidate_events"
    __table_args__ = (Index("ix_candidate_events_session", "session_id"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False)
    message_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learning_messages.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    concept_ref: Mapped[str | None] = mapped_column(String(128))
    signal: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
    ai_execution_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("ai_executions.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class IntelligenceProcessingRun(Base):
    __tablename__ = "intelligence_processing_runs"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="COMPLETED", server_default="COMPLETED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), server_default=func.now())


class IntelligenceReprocessRun(Base):
    """Auditable bounded rebuild request; source and derived rows remain immutable."""

    __tablename__ = "intelligence_reprocess_runs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_intelligence_reprocess_idempotency"),
        Index("ix_intelligence_reprocess_student_status", "student_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    # Deliberately not an FK: queue fixtures and job retention may be truncated
    # independently while this durable audit still retains the original job ID.
    job_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    version_set: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", server_default="PENDING")
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class IntelligenceReprocessSession(Base):
    """One retryable session result inside a bounded reprocessing run."""

    __tablename__ = "intelligence_reprocess_sessions"
    __table_args__ = (UniqueConstraint("reprocess_run_id", "session_id", name="uq_intelligence_reprocess_session"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    reprocess_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_reprocess_runs.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False)
    evidence_processing_run_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING", server_default="PENDING")
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IntelligenceSessionAuthority(Base):
    """Explicit default Evidence interpretation for one immutable raw session."""

    __tablename__ = "intelligence_session_authorities"
    __table_args__ = (UniqueConstraint("student_id", "session_id", name="uq_intelligence_session_authority"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False)
    reprocess_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("intelligence_reprocess_runs.id", ondelete="CASCADE"),
        nullable=True,
    )
    evidence_processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="CASCADE"), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LearningEvent(Base):
    __tablename__ = "learning_events"
    __table_args__ = (Index("ix_learning_events_run_session", "processing_run_id", "session_id"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False)
    candidate_event_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("candidate_events.id", ondelete="SET NULL")
    )
    segment_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("learning_segments.id", ondelete="RESTRICT")
    )
    segment_review_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("segment_learning_reviews.id", ondelete="RESTRICT")
    )
    segment_review_finding_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_event_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    source_message_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    concept_ref: Mapped[str | None] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_message_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learning_messages.id", ondelete="SET NULL"))


class LearningEvidence(Base):
    __tablename__ = "learning_evidence"
    __table_args__ = (Index("ix_learning_evidence_event", "event_id"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learning_events.id", ondelete="CASCADE"), nullable=False)
    concept_ref: Mapped[str | None] = mapped_column(String(128))
    dimensions: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    relationship: Mapped[str] = mapped_column(String(32), nullable=False, default="insufficient", server_default="insufficient")
    source_ref: Mapped[str] = mapped_column(String(256), nullable=False)


class CurrentLearningState(Base):
    __tablename__ = "current_learning_states"
    __table_args__ = (
        Index("ix_current_learning_states_student_status", "student_id", "status"),
        Index("ix_current_learning_states_student_subject_status", "student_id", "subject", "status"),
        Index("ix_current_learning_states_expiry", "expires_at"),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN", server_default="UNKNOWN")
    state_type: Mapped[str] = mapped_column(String(64), nullable=False)
    concept_ref: Mapped[str | None] = mapped_column(String(128))
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", server_default="ACTIVE")
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    policy_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="legacy-state-policy-v0", server_default="legacy-state-policy-v0"
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LearnerPattern(Base):
    __tablename__ = "learner_patterns"
    __table_args__ = (
        Index("ix_learner_patterns_student_status", "student_id", "status"),
        UniqueConstraint(
            "student_id",
            "policy_version",
            "pattern_type",
            "pattern_key",
            "scope_key",
            name="uq_learner_pattern_scope",
        ),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="CASCADE"), nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(64), nullable=False)
    pattern_key: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    scope_key: Mapped[str] = mapped_column(String(256), nullable=False, default="legacy", server_default="legacy")
    policy_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="legacy-pattern-policy-v0", server_default="legacy-pattern-policy-v0"
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="CANDIDATE", server_default="CANDIDATE")
    support_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    counter_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    first_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), server_default=func.now()
    )
    cycle_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), server_default=func.now()
    )
    cycle_number: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    last_supported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_challenged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PatternEvidence(Base):
    __tablename__ = "pattern_evidence"
    __table_args__ = (UniqueConstraint("pattern_id", "evidence_id", name="uq_pattern_evidence"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    pattern_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learner_patterns.id", ondelete="CASCADE"), nullable=False)
    evidence_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learning_evidence.id", ondelete="CASCADE"), nullable=False)
    relationship: Mapped[str] = mapped_column(String(32), nullable=False, default="supports", server_default="supports")
    processing_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="SET NULL")
    )
    policy_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="legacy-pattern-policy-v0", server_default="legacy-pattern-policy-v0"
    )
    task_ref: Mapped[str] = mapped_column(String(128), nullable=False, default="legacy", server_default="legacy")
    context_ref: Mapped[str] = mapped_column(String(128), nullable=False, default="legacy", server_default="legacy")
    cycle_number: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), server_default=func.now()
    )


class LearnerIntelligenceCard(Base):
    __tablename__ = "learner_intelligence_cards"
    __table_args__ = (UniqueConstraint("student_id", "processing_run_id", name="uq_intelligence_card_run"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="CASCADE"), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class DecisionView(Base):
    __tablename__ = "decision_views"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "processing_run_id",
            "subject",
            "concept_ref",
            "view_type",
            "policy_version",
            name="uq_decision_view_scope_version",
        ),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN", server_default="UNKNOWN")
    concept_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    view_type: Mapped[str] = mapped_column(String(64), nullable=False, default="learning_status", server_default="learning_status")
    conclusion: Mapped[str] = mapped_column(String(32), nullable=False, default="INSUFFICIENT_EVIDENCE", server_default="INSUFFICIENT_EVIDENCE")
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="LOW", server_default="LOW")
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    state_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    pattern_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    source_versions: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), server_default=func.now()
    )
    mastery: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)


class User(Base):
    """Stable identity record without introducing auth behavior."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint(
            "identity_provider",
            "external_subject",
            name="uq_users_identity",
        ),
        CheckConstraint(
            "role IN ('PARENT_ADMIN', 'STUDENT')",
            name="ck_users_role",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    identity_provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    external_subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="STUDENT",
        server_default="STUDENT",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Student(Base):
    """Student profile anchored to a stable user identity."""

    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_students_user_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ParentStudentRelationship(Base):
    """Explicit parent-to-student relationship foundation."""

    __tablename__ = "parent_student_relationships"
    __table_args__ = (
        UniqueConstraint(
            "parent_user_id",
            "student_id",
            name="uq_parent_student_relationship",
        ),
        Index(
            "ix_parent_student_relationships_student_id",
            "student_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    parent_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="parent",
        server_default="parent",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class GradePeriod(Base):
    """A student's active or historical grade period."""

    __tablename__ = "grade_periods"
    __table_args__ = (
        CheckConstraint(
            "grade_level BETWEEN 1 AND 12",
            name="ck_grade_periods_grade_level",
        ),
        UniqueConstraint(
            "student_id",
            "starts_on",
            name="uq_grade_periods_student_start",
        ),
        Index(
            "ix_grade_periods_student_active",
            "student_id",
            "is_active",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    student_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    grade_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
