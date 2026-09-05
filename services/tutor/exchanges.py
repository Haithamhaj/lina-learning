"""CTX-03C complete-exchange lineage and temporary vector helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
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
    segment_id: UUID | None
    student_message_id: UUID | None
    tutor_message_id: UUID
    student_content: str | None
    tutor_content: str
    student_created_at: datetime | None
    tutor_created_at: datetime

    @property
    def message_ids(self) -> tuple[UUID, ...]:
        return tuple(
            identifier
            for identifier in (self.student_message_id, self.tutor_message_id)
            if identifier is not None
        )


def serialize_exchange(exchange: ConversationExchangeContext) -> str:
    """Return the exact approved embedding representation, without metadata."""

    if exchange.student_content is None:
        raise ValueError("Only complete Student→Tutor Exchanges may be embedded.")
    return f"Student:\n{exchange.student_content}\n\nTutor:\n{exchange.tutor_content}"


def immediate_exchange_for_current_turn(
    session: Session,
    *,
    learning_session: LearningSession,
    current_turn: LearningMessage | None,
) -> ConversationExchangeContext | None:
    """Resolve CTX-02 immediate continuity independently of Segment/model lineage."""

    if current_turn is None:
        return None
    before_current = or_(
        LearningMessage.created_at < current_turn.created_at,
        (LearningMessage.created_at == current_turn.created_at) & (LearningMessage.id < current_turn.id),
    )
    tutor = session.scalar(
        select(LearningMessage)
        .where(
            LearningMessage.session_id == learning_session.id,
            LearningMessage.role == "tutor",
            before_current,
        )
        .order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())
        .limit(1)
    )
    if tutor is None:
        return None
    # A model-backed Chat turn has durable exact Student lineage.  Resolve it
    # before considering historical chronology, which prevents a later Canvas
    # Tutor message from being accidentally paired with an earlier Chat input.
    execution = session.get(AIExecution, tutor.ai_execution_id) if tutor.ai_execution_id is not None else None
    if execution is not None and execution.source_message_id is not None:
        source = session.get(LearningMessage, execution.source_message_id)
        if (
            source is not None
            and source.session_id == learning_session.id
            and source.role == "student"
        ):
            return ConversationExchangeContext(
                session_id=learning_session.id,
                segment_id=source.segment_id if source.segment_id == tutor.segment_id else None,
                student_message_id=source.id,
                tutor_message_id=tutor.id,
                student_content=source.content,
                tutor_content=tutor.content,
                student_created_at=source.created_at,
                tutor_created_at=tutor.created_at,
            )
    payload = tutor.payload if isinstance(tutor.payload, dict) else {}
    if payload.get("turn_origin") == "STUDIO_INTERACTION":
        return ConversationExchangeContext(
            session_id=learning_session.id,
            segment_id=None,
            student_message_id=None,
            tutor_message_id=tutor.id,
            student_content=None,
            tutor_content=tutor.content,
            student_created_at=None,
            tutor_created_at=tutor.created_at,
        )
    before_tutor = or_(
        LearningMessage.created_at < tutor.created_at,
        (LearningMessage.created_at == tutor.created_at) & (LearningMessage.id < tutor.id),
    )
    student = session.scalar(
        select(LearningMessage)
        .where(
            LearningMessage.session_id == learning_session.id,
            LearningMessage.role == "student",
            before_tutor,
        )
        .order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())
        .limit(1)
    )
    return ConversationExchangeContext(
        session_id=learning_session.id,
        segment_id=tutor.segment_id if student is None else student.segment_id if student.segment_id == tutor.segment_id else None,
        student_message_id=student.id if student is not None else None,
        tutor_message_id=tutor.id,
        student_content=student.content if student is not None else None,
        tutor_content=tutor.content,
        student_created_at=student.created_at if student is not None else None,
        tutor_created_at=tutor.created_at,
    )


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
