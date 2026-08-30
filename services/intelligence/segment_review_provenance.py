"""Resolve a materialized Event back to its strict Segment Review Finding."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.intelligence.consolidation import EVIDENCE_RUBRIC_VERSION
from services.intelligence.segment_reviews import (
    SEGMENT_LEARNING_REVIEW_PROMPT_VERSION,
    SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
    SEGMENT_REVIEW_POLICY_VERSION,
    SegmentReviewFinding,
    SegmentReviewValidationError,
    persisted_review_historical_anchors,
    validate_segment_review_output,
)
from services.platform.db.models import (
    CandidateEvent,
    LearningEvent,
    LearningEvidence,
    LearningMessage,
    LearningSegment,
    LearningSession,
    SegmentLearningReview,
)


def resolve_segment_review_finding(
    session: Session,
    *,
    event: LearningEvent,
    evidence: LearningEvidence,
) -> SegmentReviewFinding | None:
    """Return only the exact current-contract Finding that materialized an Event.

    This is deliberately fail-closed.  Segment Review is provenance, while
    LearningEvent and LearningEvidence remain authority; a malformed or stale
    provenance link may not confer extra derived interpretation.
    """

    if (
        event.segment_review_id is None
        or event.segment_review_finding_index is None
        or event.segment_review_finding_index < 0
        or event.segment_id is None
    ):
        return None
    review = session.get(SegmentLearningReview, event.segment_review_id)
    if review is None or not _is_current_contract(review):
        return None
    learning_session = session.get(LearningSession, event.session_id)
    segment = session.get(LearningSegment, event.segment_id)
    if (
        learning_session is None
        or segment is None
        or review.student_id != learning_session.student_id
        or review.session_id != event.session_id
        or review.segment_id != event.segment_id
        or segment.session_id != event.session_id
        or not isinstance(review.output, dict)
    ):
        return None

    messages = list(
        session.scalars(
            select(LearningMessage)
            .where(
                LearningMessage.session_id == review.session_id,
                LearningMessage.segment_id == review.segment_id,
            )
            .order_by(LearningMessage.created_at, LearningMessage.id)
        )
    )
    candidate_ids = _referenced_candidate_ids(review.output)
    if candidate_ids is None:
        return None
    candidates = (
        list(session.scalars(select(CandidateEvent).where(CandidateEvent.id.in_(candidate_ids))))
        if candidate_ids
        else []
    )
    try:
        envelope = validate_segment_review_output(
            review.output,
            messages=messages,
            candidates=candidates,
            historical_anchors=persisted_review_historical_anchors(
                session,
                learning_session=learning_session,
                segment=segment,
                review=review,
            ),
        )
    except SegmentReviewValidationError:
        return None
    if event.segment_review_finding_index >= len(envelope.findings):
        return None
    finding = envelope.findings[event.segment_review_finding_index]
    if not _has_current_lineage(
        finding=finding,
        messages=messages,
        candidates=candidates,
        review=review,
    ):
        return None
    if not _matches_materialized_provenance(
        event=event,
        evidence=evidence,
        finding=finding,
    ):
        return None
    return finding


def _is_current_contract(review: SegmentLearningReview) -> bool:
    return (
        review.status == "COMPLETED"
        and review.schema_version == SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
        and review.prompt_version == SEGMENT_LEARNING_REVIEW_PROMPT_VERSION
        and review.rubric_version == EVIDENCE_RUBRIC_VERSION
        and review.review_policy_version == SEGMENT_REVIEW_POLICY_VERSION
    )


def _referenced_candidate_ids(output: dict[str, object]) -> set[UUID] | None:
    findings = output.get("findings")
    if not isinstance(findings, list):
        return None
    identifiers: set[object] = set()
    for finding in findings:
        if not isinstance(finding, dict):
            return None
        candidate_ids = finding.get("candidate_event_ids")
        if not isinstance(candidate_ids, list):
            return None
        identifiers.update(candidate_ids)
    try:
        return {UUID(str(identifier)) for identifier in identifiers}
    except (TypeError, ValueError):
        return None


def _has_current_lineage(
    *,
    finding: SegmentReviewFinding,
    messages: list[LearningMessage],
    candidates: list[CandidateEvent],
    review: SegmentLearningReview,
) -> bool:
    if (
        len(finding.source_message_ids) != len(set(finding.source_message_ids))
        or len(finding.candidate_event_ids) != len(set(finding.candidate_event_ids))
    ):
        return False
    messages_by_id = {message.id: message for message in messages}
    candidates_by_id = {candidate.id: candidate for candidate in candidates}
    for candidate_id in finding.candidate_event_ids:
        candidate = candidates_by_id.get(candidate_id)
        source = messages_by_id.get(candidate.message_id) if candidate is not None else None
        payload = candidate.payload if candidate is not None and isinstance(candidate.payload, dict) else {}
        raw_source_ids = payload.get("source_message_ids")
        try:
            candidate_source_ids = (
                {UUID(str(identifier)) for identifier in raw_source_ids}
                if isinstance(raw_source_ids, list)
                else set()
            )
        except (TypeError, ValueError):
            return False
        if (
            candidate is None
            or candidate.session_id != review.session_id
            or source is None
            or source.role != "student"
            or source.session_id != review.session_id
            or source.segment_id != review.segment_id
            or candidate_source_ids != {source.id}
            or source.id not in finding.source_message_ids
        ):
            return False
    return True


def _matches_materialized_provenance(
    *,
    event: LearningEvent,
    evidence: LearningEvidence,
    finding: SegmentReviewFinding,
) -> bool:
    source_message_ids = [str(identifier) for identifier in finding.source_message_ids]
    candidate_event_ids = [str(identifier) for identifier in finding.candidate_event_ids]
    return (
        event.event_type == finding.validated_event_type
        and event.concept_ref == finding.concept_ref
        and event.description == finding.event_summary
        and event.source_message_ids == source_message_ids
        and event.source_message_id == finding.source_message_ids[0]
        and event.candidate_event_ids == candidate_event_ids
        and event.candidate_event_id
        == (finding.candidate_event_ids[0] if finding.candidate_event_ids else None)
        and evidence.concept_ref == finding.concept_ref
        and evidence.dimensions == finding.dimensions.model_dump(mode="json")
        and evidence.relationship == finding.relationship
        and evidence.source_ref
        == (
            f"session:{event.session_id}:segment:{event.segment_id}:"
            f"review:{event.segment_review_id}:finding:{event.segment_review_finding_index}"
        )
    )
