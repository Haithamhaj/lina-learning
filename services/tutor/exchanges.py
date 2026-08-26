"""CTX-03C complete-exchange lineage and temporary vector helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import AIExecution, LearningExchangeEmbedding, LearningMessage, LearningSegment, LearningSession


# IMPLEMENTATION CALIBRATION: controlled orthogonal/identical-vector fixtures
# distinguish zero recall from clearly related exchange text. It is deliberately
# a small, named runtime setting rather than a policy or scientific claim.
SEMANTIC_RECALL_MIN_COSINE_SIMILARITY = 0.65


@dataclass(frozen=True)
class ConversationExchangeContext:
    """One exact, completed Student→Tutor exchange from a single Segment."""

    session_id: UUID
    segment_id: UUID
    student_message_id: UUID
    tutor_message_id: UUID
    student_content: str
    tutor_content: str
    student_created_at: datetime
    tutor_created_at: datetime

    @property
    def message_ids(self) -> tuple[UUID, UUID]:
        return (self.student_message_id, self.tutor_message_id)


def serialize_exchange(exchange: ConversationExchangeContext) -> str:
    """Return the exact approved embedding representation, without metadata."""

    return f"Student:\n{exchange.student_content}\n\nTutor:\n{exchange.tutor_content}"


def persist_exchange_embedding(
    session: Session,
    *,
    student_message: LearningMessage,
    tutor_message: LearningMessage,
    embedding: list[float],
    embedding_model: str,
    ai_execution_id: UUID | None = None,
) -> LearningExchangeEmbedding:
    """Persist one validated temporary vector; raw messages remain the source."""

    if (
        student_message.role != "student"
        or tutor_message.role != "tutor"
        or student_message.session_id != tutor_message.session_id
        or student_message.segment_id is None
        or student_message.segment_id != tutor_message.segment_id
    ):
        raise ValueError("Exchange messages must share the same LearningSession and LearningSegment with Student/Tutor roles.")
    if len(embedding) != 1536 or not all(isinstance(value, (float, int)) for value in embedding):
        raise ValueError("Exchange embedding must contain exactly 1536 numeric dimensions.")
    existing = session.scalar(
        select(LearningExchangeEmbedding).where(
            LearningExchangeEmbedding.student_message_id == student_message.id,
            LearningExchangeEmbedding.tutor_message_id == tutor_message.id,
            LearningExchangeEmbedding.embedding_model == embedding_model,
        )
    )
    if existing is not None:
        return existing
    row = LearningExchangeEmbedding(
        session_id=student_message.session_id,
        segment_id=student_message.segment_id,
        student_message_id=student_message.id,
        tutor_message_id=tutor_message.id,
        embedding=[float(value) for value in embedding],
        embedding_model=embedding_model,
        dimensions=1536,
        ai_execution_id=ai_execution_id,
    )
    session.add(row)
    session.flush()
    return row


def clear_session_exchange_embeddings(
    session: Session,
    *,
    learning_session: LearningSession,
) -> None:
    """Delete only the temporary conversation index when a Session closes."""

    session.query(LearningExchangeEmbedding).filter(
        LearningExchangeEmbedding.session_id == learning_session.id
    ).delete(synchronize_session=False)
    session.flush()


def complete_exchanges_for_segment(
    session: Session,
    *,
    learning_session: LearningSession,
    segment: LearningSegment,
) -> tuple[ConversationExchangeContext, ...]:
    """Return only Tutor turns explicitly linked to a Student in this Segment."""

    if segment.session_id != learning_session.id:
        raise ValueError("LearningSegment must belong to the supplied LearningSession.")
    tutor_rows = session.execute(
        select(LearningMessage, AIExecution.source_message_id)
        .outerjoin(AIExecution, LearningMessage.ai_execution_id == AIExecution.id)
        .where(
            LearningMessage.session_id == learning_session.id,
            LearningMessage.segment_id == segment.id,
            LearningMessage.role == "tutor",
        )
        .order_by(LearningMessage.created_at, LearningMessage.id)
    ).all()
    source_ids = [source_id for _, source_id in tutor_rows if isinstance(source_id, UUID)]
    students = {
        message.id: message
        for message in session.execute(
            select(LearningMessage).where(
                LearningMessage.id.in_(source_ids) if source_ids else False,
                LearningMessage.session_id == learning_session.id,
                LearningMessage.segment_id == segment.id,
                LearningMessage.role == "student",
            )
        ).scalars()
    }
    exchanges: list[ConversationExchangeContext] = []
    for tutor, source_id in tutor_rows:
        student = students.get(source_id)
        if student is None:
            continue
        exchanges.append(
            ConversationExchangeContext(
                session_id=learning_session.id,
                segment_id=segment.id,
                student_message_id=student.id,
                tutor_message_id=tutor.id,
                student_content=student.content,
                tutor_content=tutor.content,
                student_created_at=student.created_at,
                tutor_created_at=tutor.created_at,
            )
        )
    return tuple(exchanges)
