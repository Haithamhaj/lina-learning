"""Read-only, identifier-only queries over the single AI execution ledger."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import AIExecution, CandidateEvent, ContentDocument, ContentSemanticItem, IndexedContentBlock, LearningEvidence, LearningEvent, LearningMessage, LearningSession


@dataclass(frozen=True)
class DerivedExecutionObjects:
    """Derived object identifiers only; callers load protected content separately."""

    tutor_message_ids: tuple[UUID, ...]
    candidate_event_ids: tuple[UUID, ...]
    learning_event_ids: tuple[UUID, ...]
    learning_evidence_ids: tuple[UUID, ...]
    semantic_item_ids: tuple[UUID, ...]
    indexed_block_ids: tuple[UUID, ...]


def executions_for_student(session: Session, *, student_id: UUID, learning_session_id: UUID | None = None) -> list[AIExecution]:
    """Return only one Student's directly attributable executions."""
    statement = select(AIExecution).where(AIExecution.student_id == student_id)
    if learning_session_id is not None:
        statement = statement.where(AIExecution.learning_session_id == learning_session_id)
    return list(session.execute(statement.order_by(AIExecution.created_at, AIExecution.id)).scalars())


def execution_for_tutor_message(session: Session, *, student_id: UUID, tutor_message_id: UUID) -> AIExecution | None:
    """Resolve the execution that produced a Tutor message without cross-Student lookup."""
    return session.execute(
        select(AIExecution)
        .join(LearningMessage, LearningMessage.ai_execution_id == AIExecution.id)
        .join(LearningSession, LearningSession.id == LearningMessage.session_id)
        .where(LearningMessage.id == tutor_message_id, LearningMessage.role == "tutor", LearningSession.student_id == student_id)
    ).scalar_one_or_none()


def executions_for_processing_run(session: Session, *, processing_run_id: UUID, kind: str, student_id: UUID | None = None) -> list[AIExecution]:
    """Return attempts for a named, application-owned processing-run category."""
    if kind == "intelligence":
        statement = select(AIExecution).where(AIExecution.intelligence_processing_run_id == processing_run_id)
        if student_id is not None:
            statement = statement.where(AIExecution.student_id == student_id)
    elif kind in {"semantic", "content_index"}:
        run_column = AIExecution.semantic_processing_run_id if kind == "semantic" else AIExecution.content_index_run_id
        statement = select(AIExecution).join(ContentDocument, ContentDocument.id == AIExecution.document_id).where(run_column == processing_run_id)
        if student_id is not None:
            statement = statement.where(ContentDocument.student_id == student_id)
    else:
        raise ValueError("Unsupported processing run kind.")
    return list(session.execute(statement.order_by(AIExecution.created_at, AIExecution.id)).scalars())


def derived_objects_for_execution(session: Session, *, execution: AIExecution) -> DerivedExecutionObjects:
    """Follow only durable FK lineage from one execution to produced rows."""
    tutor_messages = tuple(session.execute(select(LearningMessage.id).where(LearningMessage.ai_execution_id == execution.id)).scalars())
    candidates = tuple(session.execute(select(CandidateEvent.id).where(CandidateEvent.ai_execution_id == execution.id)).scalars())
    if execution.intelligence_processing_run_id is None:
        events: tuple[UUID, ...] = ()
        evidence: tuple[UUID, ...] = ()
    else:
        events = tuple(session.execute(select(LearningEvent.id).where(LearningEvent.processing_run_id == execution.intelligence_processing_run_id)).scalars())
        evidence = tuple(session.execute(select(LearningEvidence.id).join(LearningEvent, LearningEvidence.event_id == LearningEvent.id).where(LearningEvent.processing_run_id == execution.intelligence_processing_run_id)).scalars())
    semantic_items = () if execution.semantic_processing_run_id is None else tuple(session.execute(select(ContentSemanticItem.id).where(ContentSemanticItem.semantic_processing_run_id == execution.semantic_processing_run_id)).scalars())
    indexed_blocks = () if execution.content_index_run_id is None else tuple(session.execute(select(IndexedContentBlock.id).where(IndexedContentBlock.index_run_id == execution.content_index_run_id)).scalars())
    return DerivedExecutionObjects(tutor_messages, candidates, events, evidence, semantic_items, indexed_blocks)
