"""Durable structural closure and Review-request scheduling for Segments."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import (
    Job,
    LearningMessage,
    LearningSegment,
    LearningSession,
    Student,
)
from services.platform.jobs import enqueue_job

NEXT_SEGMENT_CREATED = "NEXT_SEGMENT_CREATED"
SESSION_CLOSED = "SESSION_CLOSED"
SEGMENT_LEARNING_REVIEW_JOB = "SEGMENT_LEARNING_REVIEW"
SEGMENT_REVIEW_REQUEST_VERSION = "segment-review-request-v3"
_CLOSURE_REASONS = frozenset({NEXT_SEGMENT_CREATED, SESSION_CLOSED})


class SegmentLifecycleError(ValueError):
    """A Segment lifecycle operation conflicts with durable lineage or history."""


def is_segment_structurally_reviewable(
    session: Session,
    *,
    learning_session: LearningSession,
    segment: LearningSegment,
) -> bool:
    """Return whether a closed Segment has the minimum raw lineage for Review."""

    if segment.session_id != learning_session.id:
        return False
    if segment.closed_at is None or segment.closure_reason not in _CLOSURE_REASONS:
        return False
    if session.get(Student, learning_session.student_id) is None:
        return False
    return session.scalar(
        select(LearningMessage.id)
        .where(
            LearningMessage.session_id == learning_session.id,
            LearningMessage.segment_id == segment.id,
            LearningMessage.role == "student",
        )
        .limit(1)
    ) is not None


def complete_segment(
    session: Session,
    *,
    learning_session: LearningSession,
    segment: LearningSegment,
    closure_reason: str,
    closed_at: datetime,
) -> Job | None:
    """Close once and enqueue the structural Segment Review request exactly once."""

    if segment.session_id != learning_session.id:
        raise SegmentLifecycleError("LearningSegment must belong to the supplied LearningSession.")
    if closure_reason not in _CLOSURE_REASONS:
        raise SegmentLifecycleError("Segment closure reason is not supported.")

    if segment.closed_at is None:
        segment.closed_at = closed_at
        segment.closure_reason = closure_reason
        session.flush()
    elif segment.closure_reason != closure_reason:
        raise SegmentLifecycleError("Segment closure reason conflicts with durable closure history.")

    if not is_segment_structurally_reviewable(
        session,
        learning_session=learning_session,
        segment=segment,
    ):
        return None

    return enqueue_job(
        session,
        job_type=SEGMENT_LEARNING_REVIEW_JOB,
        payload={
            "segment_id": str(segment.id),
            "session_id": str(learning_session.id),
            "student_id": str(learning_session.student_id),
            "review_request_version": SEGMENT_REVIEW_REQUEST_VERSION,
            "closed_at": segment.closed_at.isoformat(),
            "closure_reason": segment.closure_reason,
        },
        idempotency_key=(
            f"segment-learning-review:{segment.id}:{SEGMENT_REVIEW_REQUEST_VERSION}"
        ),
    )


def reconcile_segments_for_session_close(
    session: Session,
    *,
    learning_session: LearningSession,
    closed_at: datetime,
) -> None:
    """Close only this Session's legacy-open Segments before Session consolidation."""

    segments = list(
        session.scalars(
            select(LearningSegment)
            .where(LearningSegment.session_id == learning_session.id)
            .order_by(LearningSegment.sequence, LearningSegment.id)
        )
    )
    for index, segment in enumerate(segments):
        if segment.closed_at is None:
            reason = NEXT_SEGMENT_CREATED if index < len(segments) - 1 else SESSION_CLOSED
            complete_segment(
                session,
                learning_session=learning_session,
                segment=segment,
                closure_reason=reason,
                closed_at=closed_at,
            )
        else:
            complete_segment(
                session,
                learning_session=learning_session,
                segment=segment,
                closure_reason=segment.closure_reason or "",
                closed_at=segment.closed_at,
            )
