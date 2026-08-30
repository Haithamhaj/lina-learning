"""Deterministic activation of one complete, reviewed learning Session."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.intelligence.consolidation import EVIDENCE_RUBRIC_VERSION
from services.intelligence.current_state import apply_processing_run_current_state
from services.intelligence.decisions import apply_processing_run_decision_views
from services.intelligence.patterns import apply_processing_run_patterns
from services.intelligence.segment_reviews import (
    SEGMENT_LEARNING_REVIEW_PROMPT_VERSION,
    SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
    SEGMENT_REVIEW_POLICY_VERSION,
    SegmentLearningReviewEnvelope,
    SegmentLearningReviewV3Envelope,
    SegmentReviewValidationError,
    persisted_review_historical_anchors,
    review_completed_segment,
    validate_segment_review_output,
)
from services.model_gateway.gateway import ModelGateway
from services.platform.config import Settings
from services.platform.db.models import (
    CandidateEvent,
    CurrentLearningState,
    DecisionView,
    IntelligenceProcessingRun,
    IntelligenceSessionAuthority,
    LearnerPattern,
    LearningEvent,
    LearningEvidence,
    LearningMessage,
    LearningSegment,
    LearningSession,
    SegmentLearningReview,
)
from services.tutor.segment_lifecycle import is_segment_structurally_reviewable

SESSION_FINALIZATION_PIPELINE = "segment-finalization-v1"


class SessionFinalizationError(RuntimeError):
    """A Session cannot safely activate reviewed learning intelligence."""


class SessionFinalizationBlockedError(SessionFinalizationError):
    """The Session or its complete required Review set is not ready."""


class SessionFinalizationValidationError(SessionFinalizationError):
    """Persisted Review output or lineage is not safe to materialize."""


@dataclass(frozen=True)
class SessionFinalizationOutcome:
    processing_run: IntelligenceProcessingRun
    authority: IntelligenceSessionAuthority
    event_count: int
    evidence_count: int
    withheld_finding_count: int
    current_state_count: int
    pattern_count: int
    decision_view_count: int
    reused: bool


@dataclass(frozen=True)
class StagedSessionFinalizationOutcome:
    """One deterministic Segment-review generation, before authority activation."""

    processing_run: IntelligenceProcessingRun
    event_count: int
    evidence_count: int
    withheld_finding_count: int


@dataclass(frozen=True)
class _ValidatedReview:
    segment: LearningSegment
    review: SegmentLearningReview
    envelope: SegmentLearningReviewEnvelope


def finalize_closed_session(
    session: Session,
    *,
    learning_session: LearningSession,
) -> SessionFinalizationOutcome:
    """Atomically activate one complete Segment Review set without a model call."""

    locked_session = session.execute(
        select(LearningSession)
        .where(LearningSession.id == learning_session.id)
        .with_for_update()
    ).scalar_one_or_none()
    if locked_session is None or locked_session.student_id != learning_session.student_id:
        raise SessionFinalizationValidationError("Session finalization lineage is invalid.")
    if locked_session.status != "CLOSED" or locked_session.closed_at is None:
        raise SessionFinalizationBlockedError("Only CLOSED Sessions may be finalized.")
    if locked_session.intelligence_pipeline != SESSION_FINALIZATION_PIPELINE:
        raise SessionFinalizationBlockedError(
            "Only segment-finalization-v1 Sessions may use deterministic finalization."
        )

    existing_authority = session.execute(
        select(IntelligenceSessionAuthority)
        .where(
            IntelligenceSessionAuthority.student_id == locked_session.student_id,
            IntelligenceSessionAuthority.session_id == locked_session.id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if existing_authority is not None:
        run = session.get(
            IntelligenceProcessingRun,
            existing_authority.evidence_processing_run_id,
        )
        scope = run.scope if run is not None and isinstance(run.scope, dict) else {}
        if (
            run is None
            or run.status != "COMPLETED"
            or existing_authority.reprocess_run_id is not None
            or scope.get("session_id") != str(locked_session.id)
            or scope.get("intelligence_pipeline") != SESSION_FINALIZATION_PIPELINE
        ):
            raise SessionFinalizationValidationError(
                "Existing Session authority is not this live deterministic finalization."
            )
        return _outcome_for_existing(
            session,
            run=run,
            authority=existing_authority,
        )

    required_segments = _reviewable_segments(session, learning_session=locked_session)
    validated_reviews = _validated_required_reviews(
        session,
        learning_session=locked_session,
        required_segments=required_segments,
    )
    withheld_count = sum(
        not _is_materializable_finding(item.envelope, finding)
        for item in validated_reviews for finding in item.envelope.findings
    )

    with session.begin_nested():
        run = IntelligenceProcessingRun(
            student_id=locked_session.student_id,
            rubric_version=EVIDENCE_RUBRIC_VERSION,
            policy_version=SEGMENT_REVIEW_POLICY_VERSION,
            status="RUNNING",
            scope=_processing_scope(
                learning_session=locked_session,
                validated_reviews=validated_reviews,
            ),
        )
        session.add(run)
        session.flush()
        event_count = _materialize_eligible_findings(
            session,
            run=run,
            learning_session=locked_session,
            validated_reviews=validated_reviews,
        )
        run.status = "COMPLETED"
        authority = IntelligenceSessionAuthority(
            student_id=locked_session.student_id,
            session_id=locked_session.id,
            reprocess_run_id=None,
            evidence_processing_run_id=run.id,
            activated_at=datetime.now(UTC),
        )
        session.add(authority)
        session.flush()

        states = apply_processing_run_current_state(
            session,
            processing_run_id=run.id,
            now=locked_session.closed_at,
        )
        patterns = apply_processing_run_patterns(
            session,
            processing_run_id=run.id,
            now=locked_session.closed_at,
        )
        decisions = apply_processing_run_decision_views(
            session,
            processing_run_id=run.id,
            now=locked_session.closed_at,
        )
        session.flush()

    return SessionFinalizationOutcome(
        processing_run=run,
        authority=authority,
        event_count=event_count,
        evidence_count=event_count,
        withheld_finding_count=withheld_count,
        current_state_count=len(states),
        pattern_count=len(patterns),
        decision_view_count=len(decisions),
        reused=False,
    )


def stage_closed_session_finalization(
    session: Session,
    *,
    learning_session: LearningSession,
    review_gateway: ModelGateway | None = None,
    review_settings: Settings | None = None,
) -> StagedSessionFinalizationOutcome:
    """Materialize a fresh reviewed-Segment generation without live authority.

    Reprocessing uses this boundary to retain the existing live Session
    Authority until its complete selected scope can atomically activate.
    """

    locked_session = session.execute(
        select(LearningSession)
        .where(LearningSession.id == learning_session.id)
        .with_for_update()
    ).scalar_one_or_none()
    if locked_session is None or locked_session.student_id != learning_session.student_id:
        raise SessionFinalizationValidationError("Session finalization lineage is invalid.")
    if locked_session.status != "CLOSED" or locked_session.closed_at is None:
        raise SessionFinalizationBlockedError("Only CLOSED Sessions may be finalized.")
    if locked_session.intelligence_pipeline != SESSION_FINALIZATION_PIPELINE:
        raise SessionFinalizationBlockedError(
            "Only segment-finalization-v1 Sessions may use deterministic finalization."
        )

    required_segments = _reviewable_segments(session, learning_session=locked_session)
    try:
        validated_reviews = _validated_required_reviews(
            session,
            learning_session=locked_session,
            required_segments=required_segments,
        )
    except SessionFinalizationBlockedError:
        _refresh_unavailable_reviews(
            session,
            learning_session=locked_session,
            required_segments=required_segments,
            review_gateway=review_gateway,
            review_settings=review_settings,
        )
        validated_reviews = _validated_required_reviews(
            session,
            learning_session=locked_session,
            required_segments=required_segments,
        )
    withheld_count = sum(
        not _is_materializable_finding(item.envelope, finding)
        for item in validated_reviews for finding in item.envelope.findings
    )
    run = IntelligenceProcessingRun(
        student_id=locked_session.student_id,
        rubric_version=EVIDENCE_RUBRIC_VERSION,
        policy_version=SEGMENT_REVIEW_POLICY_VERSION,
        status="RUNNING",
        scope=_processing_scope(
            learning_session=locked_session,
            validated_reviews=validated_reviews,
        ),
    )
    session.add(run)
    session.flush()
    event_count = _materialize_eligible_findings(
        session,
        run=run,
        learning_session=locked_session,
        validated_reviews=validated_reviews,
    )
    run.status = "COMPLETED"
    session.flush()
    return StagedSessionFinalizationOutcome(
        processing_run=run,
        event_count=event_count,
        evidence_count=event_count,
        withheld_finding_count=withheld_count,
    )


def _reviewable_segments(
    session: Session,
    *,
    learning_session: LearningSession,
) -> list[LearningSegment]:
    """Return only the structurally reviewable Segment lineage for one Session."""

    return [
        segment
        for segment in session.scalars(
            select(LearningSegment)
            .where(LearningSegment.session_id == learning_session.id)
            .order_by(LearningSegment.sequence, LearningSegment.id)
            .with_for_update()
        )
        if is_segment_structurally_reviewable(
            session,
            learning_session=learning_session,
            segment=segment,
        )
    ]


def _refresh_unavailable_reviews(
    session: Session,
    *,
    learning_session: LearningSession,
    required_segments: list[LearningSegment],
    review_gateway: ModelGateway | None,
    review_settings: Settings | None,
) -> None:
    """Reuse valid current Reviews; rerun only Segments without one.

    A completed Review whose persisted output fails strict validation is *not*
    coerced or replaced here: that is a provenance/integrity failure and must
    fail closed.  Missing, stale-contract, pending, or failed Reviews are safe
    to execute again through the normal Segment Review gateway.
    """

    unavailable: list[LearningSegment] = []
    for segment in required_segments:
        try:
            _validated_required_reviews(
                session,
                learning_session=learning_session,
                required_segments=[segment],
            )
        except SessionFinalizationBlockedError:
            unavailable.append(segment)
    if not unavailable:
        return
    if review_gateway is None:
        raise SessionFinalizationBlockedError(
            "Reprocessing requires a Segment Review gateway for unavailable current Reviews."
        )
    for segment in unavailable:
        review_completed_segment(
            session,
            learning_session=learning_session,
            segment=segment,
            gateway=review_gateway,
            settings=review_settings,
        )


def _validated_required_reviews(
    session: Session,
    *,
    learning_session: LearningSession,
    required_segments: list[LearningSegment],
) -> list[_ValidatedReview]:
    if not required_segments:
        return []
    segment_ids = [segment.id for segment in required_segments]
    reviews_by_segment: dict[UUID, list[SegmentLearningReview]] = {
        segment_id: [] for segment_id in segment_ids
    }
    for review in session.scalars(
        select(SegmentLearningReview)
        .where(SegmentLearningReview.segment_id.in_(segment_ids))
        .order_by(
            SegmentLearningReview.completed_at.desc().nulls_last(),
            SegmentLearningReview.created_at.desc(),
            SegmentLearningReview.id.desc(),
        )
        .with_for_update()
    ):
        reviews_by_segment[review.segment_id].append(review)

    validated: list[_ValidatedReview] = []
    for segment in required_segments:
        reviews = reviews_by_segment[segment.id]
        if not reviews:
            raise SessionFinalizationBlockedError(
                f"Required Segment {segment.id} has no persisted Review."
            )
        compatible = [review for review in reviews if _is_compatible_review(review)]
        if not compatible:
            raise SessionFinalizationBlockedError(
                f"Required Segment {segment.id} has no contract-compatible Review."
            )
        completed = [review for review in compatible if review.status == "COMPLETED"]
        if not completed:
            statuses = sorted({review.status for review in compatible})
            raise SessionFinalizationBlockedError(
                f"Required Segment {segment.id} Review is not complete: {statuses}."
            )
        review = completed[0]
        validated.append(
            _validate_persisted_review(
                session,
                learning_session=learning_session,
                segment=segment,
                review=review,
            )
        )
    return validated


def _is_compatible_review(review: SegmentLearningReview) -> bool:
    return (
        review.schema_version == SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
        and review.prompt_version == SEGMENT_LEARNING_REVIEW_PROMPT_VERSION
        and review.rubric_version == EVIDENCE_RUBRIC_VERSION
        and review.review_policy_version == SEGMENT_REVIEW_POLICY_VERSION
    )


def _validate_persisted_review(
    session: Session,
    *,
    learning_session: LearningSession,
    segment: LearningSegment,
    review: SegmentLearningReview,
) -> _ValidatedReview:
    if (
        review.student_id != learning_session.student_id
        or review.session_id != learning_session.id
        or review.segment_id != segment.id
    ):
        raise SessionFinalizationValidationError(
            "Segment Review ownership does not match Session lineage."
        )
    if not isinstance(review.output, dict):
        raise SessionFinalizationValidationError(
            "Completed Segment Review has no strict persisted output envelope."
        )
    message_rows = list(
        session.scalars(
            select(LearningMessage)
            .where(
                LearningMessage.session_id == learning_session.id,
                LearningMessage.segment_id == segment.id,
            )
            .order_by(LearningMessage.created_at, LearningMessage.id)
        )
    )
    messages = {message.id: message for message in message_rows}
    try:
        parsed_envelope = (
            SegmentLearningReviewV3Envelope.model_validate(review.output)
            if review.output.get("version") == SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
            else SegmentLearningReviewEnvelope.model_validate(review.output)
        )
    except ValidationError as error:
        raise SessionFinalizationValidationError(
            "Persisted Segment Review output violates the strict envelope."
        ) from error
    referenced_candidate_ids = {
        candidate_id
        for finding in parsed_envelope.findings
        for candidate_id in finding.candidate_event_ids
    }
    candidate_rows = (
        list(
            session.scalars(
                select(CandidateEvent).where(
                    CandidateEvent.id.in_(referenced_candidate_ids)
                )
            )
        )
        if referenced_candidate_ids
        else []
    )
    candidates = {candidate.id: candidate for candidate in candidate_rows}
    try:
        envelope = validate_segment_review_output(
            review.output,
            messages=message_rows,
            candidates=candidate_rows,
            historical_anchors=persisted_review_historical_anchors(
                session,
                learning_session=learning_session,
                segment=segment,
                review=review,
            ),
        )
    except SegmentReviewValidationError as error:
        raise SessionFinalizationValidationError(
            "Persisted Segment Review Finding violates the compiled validation contract."
        ) from error
    for finding in envelope.findings:
        _validate_finding_lineage(
            finding_source_ids=finding.source_message_ids,
            finding_candidate_ids=finding.candidate_event_ids,
            learning_session=learning_session,
            segment=segment,
            messages=messages,
            candidates=candidates,
        )
    return _ValidatedReview(segment=segment, review=review, envelope=envelope)


def _validate_finding_lineage(
    *,
    finding_source_ids: list[UUID],
    finding_candidate_ids: list[UUID],
    learning_session: LearningSession,
    segment: LearningSegment,
    messages: dict[UUID, LearningMessage],
    candidates: dict[UUID, CandidateEvent],
) -> None:
    if len(finding_source_ids) != len(set(finding_source_ids)) or len(
        finding_candidate_ids
    ) != len(set(finding_candidate_ids)):
        raise SessionFinalizationValidationError("Finding lineage contains duplicate IDs.")
    sources = [messages.get(message_id) for message_id in finding_source_ids]
    if any(source is None for source in sources) or not any(
        source is not None and source.role == "student" for source in sources
    ):
        raise SessionFinalizationValidationError(
            "Finding source Message lineage is outside its raw Segment."
        )
    for candidate_id in finding_candidate_ids:
        candidate = candidates.get(candidate_id)
        if candidate is None or candidate.session_id != learning_session.id:
            raise SessionFinalizationValidationError(
                "Finding Candidate lineage is outside its Session."
            )
        candidate_source = messages.get(candidate.message_id)
        payload = candidate.payload if isinstance(candidate.payload, dict) else {}
        raw_source_ids = payload.get("source_message_ids")
        try:
            candidate_source_ids = (
                {UUID(str(value)) for value in raw_source_ids}
                if isinstance(raw_source_ids, list)
                else set()
            )
        except (TypeError, ValueError) as error:
            raise SessionFinalizationValidationError(
                "Finding Candidate source lineage is malformed."
            ) from error
        if (
            candidate_source is None
            or candidate_source.session_id != learning_session.id
            or candidate_source.segment_id != segment.id
            or candidate_source.role != "student"
            or candidate_source_ids != {candidate_source.id}
            or candidate_source.id not in finding_source_ids
        ):
            raise SessionFinalizationValidationError(
                "Finding Candidate source lineage is outside its raw Segment."
            )


def _processing_scope(
    *,
    learning_session: LearningSession,
    validated_reviews: list[_ValidatedReview],
) -> dict[str, object]:
    return {
        "session_id": str(learning_session.id),
        "intelligence_pipeline": SESSION_FINALIZATION_PIPELINE,
        "segment_review_schema_version": SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
        "segment_review_prompt_version": SEGMENT_LEARNING_REVIEW_PROMPT_VERSION,
        "segment_review_rubric_version": EVIDENCE_RUBRIC_VERSION,
        "segment_review_policy_version": SEGMENT_REVIEW_POLICY_VERSION,
        "required_segment_ids": [str(item.segment.id) for item in validated_reviews],
        "segment_review_ids": [str(item.review.id) for item in validated_reviews],
        "review_execution_routes": [
            {"provider": provider, "model": model}
            for provider, model in sorted(
                {(item.review.provider, item.review.model) for item in validated_reviews}
            )
        ],
    }


def _materialize_eligible_findings(
    session: Session,
    *,
    run: IntelligenceProcessingRun,
    learning_session: LearningSession,
    validated_reviews: list[_ValidatedReview],
) -> int:
    event_count = 0
    for item in validated_reviews:
        for finding_index, finding in enumerate(item.envelope.findings):
            if not _is_materializable_finding(item.envelope, finding):
                continue
            source_message_ids = [str(message_id) for message_id in finding.source_message_ids]
            candidate_event_ids = [str(candidate_id) for candidate_id in finding.candidate_event_ids]
            event = LearningEvent(
                processing_run_id=run.id,
                session_id=learning_session.id,
                candidate_event_id=(finding.candidate_event_ids[0] if finding.candidate_event_ids else None),
                segment_id=item.segment.id,
                segment_review_id=item.review.id,
                segment_review_finding_index=finding_index,
                candidate_event_ids=candidate_event_ids,
                source_message_ids=source_message_ids,
                subject=item.envelope.primary_broad_subject,
                concept_ref=finding.concept_ref,
                event_type=finding.validated_event_type,
                description=finding.event_summary,
                source_message_id=finding.source_message_ids[0],
            )
            session.add(event)
            session.flush()
            session.add(
                LearningEvidence(
                    event_id=event.id,
                    concept_ref=finding.concept_ref,
                    dimensions=finding.dimensions.model_dump(mode="json"),
                    relationship=finding.relationship,
                    source_ref=(
                        f"session:{learning_session.id}:segment:{item.segment.id}:"
                        f"review:{item.review.id}:finding:{finding_index}"
                    ),
                )
            )
            event_count += 1
    session.flush()
    return event_count


def _is_materializable_finding(
    envelope: SegmentLearningReviewEnvelope,
    finding: object,
) -> bool:
    """Fail closed unless one v3 Learning Review owns the Finding's Subject."""

    if envelope.segment_kind != "LEARNING" or envelope.primary_broad_subject is None:
        return False
    reported_broad_subject = getattr(finding, "reported_broad_subject", None)
    if reported_broad_subject not in (None, envelope.primary_broad_subject):
        return False
    if envelope.version == SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION:
        return True
    return getattr(finding, "subject_alignment", None) in (None, "SAME_AS_SESSION")


def _outcome_for_existing(
    session: Session,
    *,
    run: IntelligenceProcessingRun,
    authority: IntelligenceSessionAuthority,
) -> SessionFinalizationOutcome:
    event_count = session.scalar(
        select(func.count(LearningEvent.id)).where(LearningEvent.processing_run_id == run.id)
    ) or 0
    evidence_count = session.scalar(
        select(func.count(LearningEvidence.id))
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .where(LearningEvent.processing_run_id == run.id)
    ) or 0
    scope = run.scope if isinstance(run.scope, dict) else {}
    review_ids = [UUID(str(value)) for value in scope.get("segment_review_ids", [])]
    withheld_count = 0
    if review_ids:
        for review in session.scalars(
            select(SegmentLearningReview).where(SegmentLearningReview.id.in_(review_ids))
        ):
            if isinstance(review.output, dict):
                try:
                    envelope = (
                        SegmentLearningReviewV3Envelope.model_validate(review.output)
                        if review.output.get("version") == SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
                        else SegmentLearningReviewEnvelope.model_validate(review.output)
                    )
                except ValidationError as error:
                    raise SessionFinalizationValidationError(
                        "Authoritative Review no longer has a strict persisted envelope."
                    ) from error
                withheld_count += sum(
                    not _is_materializable_finding(envelope, finding)
                    for finding in envelope.findings
                )
    return SessionFinalizationOutcome(
        processing_run=run,
        authority=authority,
        event_count=event_count,
        evidence_count=evidence_count,
        withheld_finding_count=withheld_count,
        current_state_count=session.scalar(
            select(func.count(CurrentLearningState.id)).where(
                CurrentLearningState.processing_run_id == run.id
            )
        ) or 0,
        pattern_count=session.scalar(
            select(func.count(LearnerPattern.id)).where(LearnerPattern.processing_run_id == run.id)
        ) or 0,
        decision_view_count=session.scalar(
            select(func.count(DecisionView.id)).where(DecisionView.processing_run_id == run.id)
        ) or 0,
        reused=True,
    )
