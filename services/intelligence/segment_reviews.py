"""Persistence-only ownership validation for versioned Segment Learning Reviews."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.platform.db.models import LearningSegment, LearningSession, SegmentLearningReview


class SegmentLearningReviewLineageError(ValueError):
    """Raised when review ownership would contradict durable Session/Segment lineage."""


def create_segment_learning_review(
    session: Session,
    *,
    student_id: UUID,
    session_id: UUID,
    segment_id: UUID,
    schema_version: str,
    prompt_version: str,
    rubric_version: str,
    review_policy_version: str,
    provider: str,
    model: str,
) -> SegmentLearningReview:
    """Stage a pending Review only when Student, Session, and Segment ownership agree."""

    learning_session = session.get(LearningSession, session_id)
    if learning_session is None or learning_session.student_id != student_id:
        raise SegmentLearningReviewLineageError("LearningSession does not belong to the supplied Student.")
    segment = session.get(LearningSegment, segment_id)
    if segment is None or segment.session_id != learning_session.id:
        raise SegmentLearningReviewLineageError("LearningSegment does not belong to the supplied LearningSession.")

    if segment.closed_at is None or segment.closure_reason is None:
        raise SegmentLearningReviewLineageError(
            "LearningSegment must be durably closed before a SegmentLearningReview can be created."
        )

    review = SegmentLearningReview(
        student_id=student_id,
        session_id=session_id,
        segment_id=segment_id,
        schema_version=schema_version,
        prompt_version=prompt_version,
        rubric_version=rubric_version,
        review_policy_version=review_policy_version,
        provider=provider,
        model=model,
        status="PENDING",
    )
    session.add(review)
    return review
