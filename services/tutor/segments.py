"""Small durable helpers for CTX-03A session-local Segment lineage."""

from __future__ import annotations

from enum import Enum
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from services.platform.db.models import LearningMessage, LearningSegment, LearningSession
from services.tutor.segment_lifecycle import NEXT_SEGMENT_CREATED, complete_segment


class SegmentAssignmentError(ValueError):
    """A message cannot be attached to a Segment outside its immutable lineage."""


class StructuredSegmentStateError(ValueError):
    """A candidate Segment State is not compact, typed, or source-linked."""


class SegmentRelation(str, Enum):
    """Luna's semantic relation of the current Student turn to this Session."""

    CONTINUE = "CONTINUE"
    NEW_SEGMENT = "NEW_SEGMENT"
    UNCERTAIN = "UNCERTAIN"


SEGMENT_RELATION_SCHEMA_VERSION = "segment-relation-v1"
SEGMENT_STATE_SCHEMA_VERSION = "structured-segment-state-v1"
MAX_SEGMENT_STATE_TEXT = 500
MAX_SEGMENT_STATE_REFERENCES = 6
MAX_SEGMENT_STATE_FACTS = 6
MAX_SEGMENT_STATE_SOURCE_MESSAGES = 8


class StructuredSegmentState(BaseModel):
    """Replaceable latest orientation for one Segment, never learner intelligence."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["structured-segment-state-v1"]
    active_goal: str | None = Field(default=None, min_length=1, max_length=MAX_SEGMENT_STATE_TEXT)
    unresolved_point: str | None = Field(default=None, min_length=1, max_length=MAX_SEGMENT_STATE_TEXT)
    active_references: list[str] = Field(default_factory=list, max_length=MAX_SEGMENT_STATE_REFERENCES)
    established_facts: list[str] = Field(default_factory=list, max_length=MAX_SEGMENT_STATE_FACTS)
    source_message_ids: list[UUID] = Field(min_length=1, max_length=MAX_SEGMENT_STATE_SOURCE_MESSAGES)

    @staticmethod
    def _bounded_items(values: list[str]) -> list[str]:
        if any(not value or len(value) > MAX_SEGMENT_STATE_TEXT for value in values):
            raise ValueError("Structured Segment State items must be bounded non-empty text.")
        return values

    @field_validator("active_references")
    @classmethod
    def _validate_references(cls, value: list[str]) -> list[str]:
        return cls._bounded_items(value)

    @field_validator("established_facts")
    @classmethod
    def _validate_facts(cls, value: list[str]) -> list[str]:
        return cls._bounded_items(value)


def latest_segment_for_session(session: Session, *, session_id: UUID) -> LearningSegment | None:
    """Return the most recently sequenced Segment for exactly one Session."""

    if hasattr(session, "scalars"):
        statement = (
            select(LearningSegment)
            .where(LearningSegment.session_id == session_id)
            .order_by(LearningSegment.sequence.desc(), LearningSegment.id.desc())
            .limit(1)
        )
        return session.scalars(statement).first()
    rows = [
        row for row in getattr(session, "rows", ())
        if isinstance(row, LearningSegment) and row.session_id == session_id
    ]
    return max(rows, key=lambda row: (row.sequence, str(row.id)), default=None)


def create_next_segment(session: Session, *, learning_session: LearningSession) -> LearningSegment:
    """Create the next contiguous Segment while locking its owning Session row."""

    if hasattr(session, "execute"):
        session.execute(
            select(LearningSession.id)
            .where(LearningSession.id == learning_session.id)
            .with_for_update()
        ).scalar_one()
    latest = latest_segment_for_session(session, session_id=learning_session.id)
    if latest is not None:
        complete_segment(
            session,
            learning_session=learning_session,
            segment=latest,
            closure_reason=NEXT_SEGMENT_CREATED,
            closed_at=datetime.now(UTC),
        )
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


def parse_structured_segment_state(
    payload: object,
    *,
    allowed_source_message_ids: set[UUID],
) -> StructuredSegmentState:
    """Validate a narrow, same-Segment state projection before it is persisted."""

    try:
        state = StructuredSegmentState.model_validate(payload)
    except ValidationError as error:
        raise StructuredSegmentStateError("Structured Segment State violates the contract.") from error
    if not set(state.source_message_ids).issubset(allowed_source_message_ids):
        raise StructuredSegmentStateError("Structured Segment State references raw messages outside its Segment.")
    return state


def latest_valid_structured_segment_state(
    session: Session,
    *,
    segment: LearningSegment | None,
) -> StructuredSegmentState | None:
    """Return only a valid latest projection whose raw sources remain in this Segment."""

    if segment is None or segment.structured_state is None:
        return None
    if hasattr(session, "scalars"):
        source_ids = set(session.scalars(
            select(LearningMessage.id).where(LearningMessage.segment_id == segment.id)
        ))
    else:
        source_ids = {
            row.id for row in getattr(session, "rows", ())
            if isinstance(row, LearningMessage) and row.segment_id == segment.id
        }
    try:
        return parse_structured_segment_state(
            segment.structured_state,
            allowed_source_message_ids=source_ids,
        )
    except StructuredSegmentStateError:
        return None
