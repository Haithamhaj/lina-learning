"""Foundational SQLAlchemy models.

Authentication, authorization roles, learning data, and content models belong
to later tasks. These models only establish durable identity and grade-period
relationships needed by the Phase 0 database foundation.
"""

from datetime import UTC, date, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector


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
    """Immutable operational record for one Model Gateway request."""

    __tablename__ = "ai_executions"
    __table_args__ = (
        Index("ix_ai_executions_task_created", "task", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    task: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    latency_ms: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    estimated_cost_usd: Mapped[float | None] = mapped_column(nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
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
        UniqueConstraint("document_id", "kind", "processor_version", name="uq_content_processing_run_version"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("content_documents.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    processor_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", server_default="PENDING")
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CurriculumNode(Base):
    """A normalized Grade-local curriculum concept with source provenance."""

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
    """A source-linked retrieval unit; embeddings are added by TASK-013."""

    __tablename__ = "content_blocks"
    __table_args__ = (
        Index("ix_content_blocks_document_run", "document_id", "processing_run_id"),
        Index("ix_content_blocks_embedding", "embedding", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_l2_ops"}),
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
    embedding: Mapped[list[float] | None] = mapped_column(Vector(8), nullable=True)


class LearningSession(Base):
    """Raw-session envelope; downstream intelligence remains derived."""

    __tablename__ = "learning_sessions"
    __table_args__ = (Index("ix_learning_sessions_student_status", "student_id", "status"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str] = mapped_column(String(32), nullable=False, default="MATH", server_default="MATH")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN", server_default="OPEN")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LearningMessage(Base):
    __tablename__ = "learning_messages"
    __table_args__ = (Index("ix_learning_messages_session_created", "session_id", "created_at"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
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


class LearningEvent(Base):
    __tablename__ = "learning_events"
    __table_args__ = (Index("ix_learning_events_run_session", "processing_run_id", "session_id"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False)
    candidate_event_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("candidate_events.id", ondelete="CASCADE"), nullable=False)
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
    __table_args__ = (Index("ix_current_learning_states_student_status", "student_id", "status"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="CASCADE"), nullable=False)
    state_type: Mapped[str] = mapped_column(String(64), nullable=False)
    concept_ref: Mapped[str | None] = mapped_column(String(128))
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", server_default="ACTIVE")
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")


class LearnerPattern(Base):
    __tablename__ = "learner_patterns"
    __table_args__ = (Index("ix_learner_patterns_student_status", "student_id", "status"), UniqueConstraint("student_id", "processing_run_id", "pattern_type", "pattern_key", "scope", name="uq_learner_pattern_scope"))
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="CASCADE"), nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(64), nullable=False)
    pattern_key: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="CANDIDATE", server_default="CANDIDATE")
    support_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    counter_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    detail: Mapped[str] = mapped_column(Text, nullable=False)


class PatternEvidence(Base):
    __tablename__ = "pattern_evidence"
    __table_args__ = (UniqueConstraint("pattern_id", "evidence_id", name="uq_pattern_evidence"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    pattern_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learner_patterns.id", ondelete="CASCADE"), nullable=False)
    evidence_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("learning_evidence.id", ondelete="CASCADE"), nullable=False)


class LearnerIntelligenceCard(Base):
    __tablename__ = "learner_intelligence_cards"
    __table_args__ = (UniqueConstraint("student_id", "processing_run_id", name="uq_intelligence_card_run"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="CASCADE"), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class DecisionView(Base):
    __tablename__ = "decision_views"
    __table_args__ = (UniqueConstraint("student_id", "processing_run_id", "concept_ref", name="uq_decision_view_run_concept"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    processing_run_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("intelligence_processing_runs.id", ondelete="CASCADE"), nullable=False)
    concept_ref: Mapped[str] = mapped_column(String(128), nullable=False)
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
