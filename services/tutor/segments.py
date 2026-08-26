"""Small durable helpers for CTX-03A session-local Segment lineage."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import LearningMessage, LearningSegment, LearningSession


class SegmentAssignmentError(ValueError):
    """A message cannot be attached to a Segment outside its immutable lineage."""


def latest_segment_for_session(session: Session, *, session_id: UUID) -> LearningSegment | None:
    """Return the most recently sequenced Segment for exactly one Session."""

    statement = (
        select(LearningSegment)
        .where(LearningSegment.session_id == session_id)
        .order_by(LearningSegment.sequence.desc(), LearningSegment.id.desc())
        .limit(1)
    )
    return session.scalars(statement).first()


def create_next_segment(session: Session, *, learning_session: LearningSession) -> LearningSegment:
    """Create the next contiguous Segment while locking its owning Session row."""

    session.execute(
        select(LearningSession.id)
        .where(LearningSession.id == learning_session.id)
        .with_for_update()
    ).scalar_one()
    latest = latest_segment_for_session(session, session_id=learning_session.id)
    segment = LearningSegment(
        session_id=learning_session.id,
        sequence=1 if latest is None else latest.sequence + 1,
    )
    session.add(segment)
    session.flush()
    return segment


def assign_message_to_segment(
    session: Session,
    *,
    message: LearningMessage,
    segment: LearningSegment,
) -> LearningMessage:
    """Assign an unsegmented message once, without cross-session or overwrite paths."""

    if message.session_id != segment.session_id:
        raise SegmentAssignmentError("LearningMessage and LearningSegment must belong to the same LearningSession")
    if message.segment_id is not None and message.segment_id != segment.id:
        raise SegmentAssignmentError("LearningMessage already belongs to a different LearningSegment")
    if message.segment_id is None:
        message.segment_id = segment.id
        session.flush()
    return message
