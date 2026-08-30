"""Staged, source-grounded semantic Review for one completed Segment."""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, get_args
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.intelligence.consolidation import (
    EVIDENCE_RUBRIC_VERSION,
    EvidenceDimensions,
    EvidenceRelationship,
)
from services.intelligence.subjects import (
    BROAD_SUBJECT_REGISTRY_VERSION,
    BROAD_SUBJECT_KEYS,
    is_supported_broad_subject,
)
from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.config import Settings, get_settings
from services.platform.db.models import (
    CandidateEvent,
    IntelligenceProcessingRun,
    IntelligenceReprocessRun,
    IntelligenceSessionAuthority,
    LearningEvent,
    LearningEvidence,
    LearningMessage,
    LearningSegment,
    LearningSession,
    ModelTask,
    SegmentLearningReview,
    Student,
)
from services.tutor.candidate_events import (
    CANDIDATE_EVENT_SCHEMA_VERSION,
    MISCONCEPTION_EVIDENCE_SCHEMA_VERSION,
    CandidateEventMetadataItem,
    CandidateEventType,
    MisconceptionEvidence,
    persisted_guided_learning_check,
)
from services.tutor.teaching_methods import (
    TEACHING_METHOD_REGISTRY_VERSION,
    TeachingMethod,
    is_supported_teaching_method,
)

LEGACY_SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION = "segment-learning-review-v2"
SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION = "segment-learning-review-v3"
SEGMENT_LEARNING_REVIEW_PROMPT_VERSION = "segment-learning-review-prompt-v8"
SEGMENT_REVIEW_POLICY_VERSION = "segment-review-policy-v3"
HISTORICAL_ANCHOR_LIMIT = 8
MEANINGFUL_RETENTION_DELAY = timedelta(days=7)

SegmentReviewEventType = Literal[
    "learning_attempt", "independent_success", "guided_success", "incorrect_attempt",
    "misconception_signal", "self_correction", "explanation_attempt", "transfer_attempt",
    "retention_check", "strategy_applied", "strategy_outcome", "support_change", "open_loop_created",
    "open_loop_resolved", "extended_learning_event",
]
TransferContext = Literal["not_tested", "near_identical", "meaningfully_changed"]
RetentionContext = Literal["not_tested", "meaningfully_delayed"]
SubjectAlignment = Literal["SAME_AS_SESSION", "POSSIBLE_CROSS_SUBJECT", "UNCERTAIN"]
SegmentKind = Literal["LEARNING", "NON_LEARNING"]
SchoolRelation = Literal["SCHOOL_ALIGNED", "EXTENDED", "UNKNOWN"]
_SUPPORTED_SEGMENT_CANDIDATE_TYPES = frozenset(get_args(CandidateEventType)) - {"retention_check"}


class SegmentReviewError(RuntimeError):
    """A controlled Segment Review failure safe to persist and retry."""


class SegmentReviewLineageError(SegmentReviewError):
    """The supplied Review ownership or raw input is not durable and valid."""


class SegmentReviewValidationError(SegmentReviewError):
    """Model output does not satisfy the compiled source-grounding contract."""


class SegmentReviewCapacityError(SegmentReviewError):
    """The complete serialized Segment request exceeds its calibrated capacity."""


class SegmentReviewProviderError(SegmentReviewError):
    """The provider failed without exposing its raw error in Review state."""


class UnsupportedSegmentReviewContract(SegmentReviewError):
    """The requested semantic identity is not compiled into this process."""


class SegmentLearningReviewLineageError(ValueError):
    """Raised when review ownership would contradict durable Session/Segment lineage."""


class SegmentReviewFinding(BaseModel):
    """Shared v3 Finding semantics, never durable intelligence by themselves."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    validated_event_type: SegmentReviewEventType
    concept_ref: str | None = Field(..., min_length=1, max_length=128)
    event_summary: str = Field(..., min_length=1, max_length=800)
    source_message_ids: list[UUID] = Field(..., min_length=1, max_length=16)
    candidate_event_ids: list[UUID] = Field(..., max_length=16)
    historical_anchor_evidence_ids: list[UUID] = Field(..., max_length=HISTORICAL_ANCHOR_LIMIT)
    transfer_context: TransferContext
    retention_context: RetentionContext
    dimensions: EvidenceDimensions
    relationship: EvidenceRelationship
    # A non-authoritative compatibility/model claim used only for conflict detection.
    reported_broad_subject: str | None = Field(...)
    teaching_method_id: TeachingMethod | None = Field(...)
    teaching_method_source_tutor_message_id: UUID | None = Field(...)
    misconception_evidence: MisconceptionEvidence | None = Field(...)

    @model_validator(mode="after")
    def enforce_local_contract(self) -> SegmentReviewFinding:
        forbidden = ("visual learner", "learning style", "highly intelligent", "poor attention", "careless", "low motivation", "personality", "adhd")
        if any(label in self.event_summary.casefold() for label in forbidden):
            raise ValueError("Finding summary contains an unsupported learner label.")
        if self.validated_event_type != "misconception_signal" and self.misconception_evidence is not None:
            raise ValueError("Only misconception findings may contain misconception evidence.")
        if self.reported_broad_subject is not None and not is_supported_broad_subject(
            self.reported_broad_subject
        ):
            raise ValueError("Finding Subject claim is outside the Broad Subject registry.")
        return self


class LegacySegmentReviewFinding(SegmentReviewFinding):
    """v2-only Finding fields retained for historical audit parsing."""

    school_or_extended: Literal["school", "extended"]
    subject_alignment: SubjectAlignment | None = Field(...)

    @model_validator(mode="after")
    def enforce_legacy_school_contract(self) -> LegacySegmentReviewFinding:
        if self.validated_event_type == "extended_learning_event" and self.school_or_extended != "extended":
            raise ValueError("extended_learning_event must be marked extended.")
        return self


class SegmentReviewFindingV3(SegmentReviewFinding):
    """v3 Finding deliberately excludes legacy relative-school fields."""


class SegmentSchoolContext(BaseModel):
    """Optional school alignment metadata; it never supplies teaching authority."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    school_relation: SchoolRelation
    school_subject_ref: str | None = Field(..., min_length=1, max_length=128)
    school_domain_path: list[str] = Field(..., max_length=16)
    unit_ref: str | None = Field(..., min_length=1, max_length=128)
    lesson_ref: str | None = Field(..., min_length=1, max_length=128)
    page_refs: list[str] = Field(..., max_length=32)
    source_refs: list[str] = Field(..., max_length=32)

    @model_validator(mode="after")
    def require_provenance_for_school_structure(self) -> SegmentSchoolContext:
        has_structure = any(
            (
                self.school_subject_ref,
                self.school_domain_path,
                self.unit_ref,
                self.lesson_ref,
                self.page_refs,
            )
        )
        if self.school_relation == "UNKNOWN" and (has_structure or self.source_refs):
            raise ValueError("UNKNOWN school context must not carry school structure or sources.")
        if self.school_relation != "UNKNOWN" and not self.source_refs:
            raise ValueError("School structure requires trusted source provenance.")
        return self


class SegmentLearningReviewEnvelope(BaseModel):
    """The strict, versioned staged output accepted from the Segment Reviewer."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[
        LEGACY_SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
        SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
    ]
    segment_kind: SegmentKind | None = Field(...)
    primary_broad_subject: str | None = Field(...)
    school_context: SegmentSchoolContext | None = Field(...)
    findings: list[LegacySegmentReviewFinding] = Field(..., max_length=24)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_v2(cls, value: object) -> object:
        if not isinstance(value, dict) or value.get("version") != LEGACY_SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION:
            return value
        normalized = dict(value)
        normalized.setdefault("segment_kind", None)
        normalized.setdefault("primary_broad_subject", None)
        normalized.setdefault("school_context", None)
        raw_findings = normalized.get("findings")
        if isinstance(raw_findings, list):
            normalized["findings"] = [
                {**finding, "reported_broad_subject": finding.get("reported_broad_subject")}
                if isinstance(finding, dict)
                else finding
                for finding in raw_findings
            ]
        return normalized

    @model_validator(mode="after")
    def enforce_subject_attribution_contract(self) -> SegmentLearningReviewEnvelope:
        if self.version == LEGACY_SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION:
            return self
        if self.segment_kind is None:
            raise ValueError("v3 Reviews must declare a Segment kind.")
        if self.segment_kind == "LEARNING":
            if not is_supported_broad_subject(self.primary_broad_subject):
                raise ValueError("Learning Reviews require a supported primary Broad Subject.")
            if self.school_context is None:
                raise ValueError("Learning Reviews require an explicit School Context.")
            return self
        if self.primary_broad_subject is not None or self.school_context is not None or self.findings:
            raise ValueError("Non-Learning Reviews have no academic Subject or Findings.")
        return self


class SegmentLearningReviewV3Envelope(SegmentLearningReviewEnvelope):
    """The only Review shape accepted from the live v3 model route.

    The parent envelope intentionally continues to parse v2 rows for audit and
    reprocessing lineage.  Keeping the live response schema separate prevents
    a provider from returning a historical contract to a v3 Review run.
    """

    version: Literal[SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION]
    school_context: SegmentSchoolContext | None = Field(...)
    findings: list[SegmentReviewFindingV3] = Field(..., max_length=24)


@dataclass(frozen=True)
class HistoricalEvidenceAnchor:
    """Minimal, prior Session-authorized retention context for one Review."""

    evidence_id: UUID
    broad_subject: str
    concept_ref: str
    prior_demonstration_state: str
    prior_observed_at: datetime
    elapsed_time: str
    reason_for_inclusion: str = "prior_session_authorized_demonstration"

    def model_input(self) -> dict[str, str]:
        return {
            "prior_evidence_id": str(self.evidence_id),
            "broad_subject": self.broad_subject,
            "concept_ref": self.concept_ref,
            "prior_demonstration_state": self.prior_demonstration_state,
            "prior_observed_at": self.prior_observed_at.isoformat(),
            "elapsed_time": self.elapsed_time,
            "reason_for_inclusion": self.reason_for_inclusion,
        }


SEGMENT_REVIEW_RESPONSE_SCHEMA: dict[str, object] = {
    "name": "segment_learning_review_v3",
    "schema": SegmentLearningReviewV3Envelope.model_json_schema(),
}


@dataclass(frozen=True)
class SegmentReviewVersion:
    schema_version: str = SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
    prompt_version: str = SEGMENT_LEARNING_REVIEW_PROMPT_VERSION
    rubric_version: str = EVIDENCE_RUBRIC_VERSION
    policy_version: str = SEGMENT_REVIEW_POLICY_VERSION
    provider: str | None = None
    model: str | None = None


@dataclass(frozen=True)
class SegmentReviewOutcome:
    review: SegmentLearningReview
    finding_count: int
    model_called: bool


_EXECUTABLE_REVIEW_VERSION = SegmentReviewVersion()


def create_segment_learning_review(
    session: Session, *, student_id: UUID, session_id: UUID, segment_id: UUID,
    schema_version: str, prompt_version: str, rubric_version: str,
    review_policy_version: str, provider: str, model: str,
) -> SegmentLearningReview:
    """Stage a pending Review only when Student, Session, and Segment ownership agree."""

    learning_session = session.get(LearningSession, session_id)
    if learning_session is None or learning_session.student_id != student_id:
        raise SegmentLearningReviewLineageError("LearningSession does not belong to the supplied Student.")
    segment = session.get(LearningSegment, segment_id)
    if segment is None or segment.session_id != learning_session.id:
        raise SegmentLearningReviewLineageError("LearningSegment does not belong to the supplied LearningSession.")
    if segment.closed_at is None or segment.closure_reason is None:
        raise SegmentLearningReviewLineageError("LearningSegment must be durably closed before a SegmentLearningReview can be created.")
    review = SegmentLearningReview(
        student_id=student_id, session_id=session_id, segment_id=segment_id,
        schema_version=schema_version, prompt_version=prompt_version,
        rubric_version=rubric_version, review_policy_version=review_policy_version,
        provider=provider, model=model, status="PENDING",
    )
    session.add(review)
    return review


def review_completed_segment(
    session: Session, *, learning_session: LearningSession, segment: LearningSegment,
    gateway: ModelGateway, version: SegmentReviewVersion | None = None,
    settings: Settings | None = None,
) -> SegmentReviewOutcome:
    """Interpret a complete raw Segment and persist only validated staged output."""

    route = gateway.route_for(ModelTask.SEGMENT_EVIDENCE)
    selected = version or SegmentReviewVersion(provider=route.provider, model=route.model)
    _require_supported_version(selected, provider=route.provider, model=route.model)
    review = _find_or_create_review(session, learning_session=learning_session, segment=segment, version=selected, provider=route.provider, model=route.model)
    if review.status == "COMPLETED":
        return SegmentReviewOutcome(review=review, finding_count=_finding_count(review), model_called=False)

    review.status, review.output, review.ai_execution_id, review.completed_at, review.failure_detail = "RUNNING", None, None, None, None
    session.flush()
    try:
        messages = _complete_raw_segment(session, learning_session=learning_session, segment=segment)
        candidates = _valid_candidate_hints(session, learning_session=learning_session, messages=messages)
        historical_anchors = _historical_anchors(
            session,
            learning_session=learning_session,
            segment=segment,
        )
        payload = _model_payload(
            learning_session=learning_session,
            segment=segment,
            messages=messages,
            candidates=candidates,
            historical_anchors=historical_anchors,
        )
        _enforce_capacity(payload, settings=settings)
        result = gateway.execute(
            ModelTask.SEGMENT_EVIDENCE,
            payload,
            lineage=AIExecutionLineage(
                operation="segment_learning_review",
                operation_id=uuid5(NAMESPACE_URL, f"segment-learning-review:{review.id}"),
                student_id=review.student_id,
                learning_session_id=review.session_id,
                source_candidate_event_ids=tuple(candidate.id for candidate in candidates),
            ),
        )
        envelope = validate_live_segment_review_output(
            result.output,
            messages=messages,
            candidates=candidates,
            historical_anchors=historical_anchors,
        )
    except SegmentReviewError as error:
        mark_segment_review_failed(session, review=review, error=error)
        raise
    except Exception as error:
        controlled = SegmentReviewProviderError("SegmentReviewProviderError")
        mark_segment_review_failed(session, review=review, error=controlled)
        raise controlled from error

    review.status = "COMPLETED"
    review.output = envelope.model_dump(mode="json")
    review.ai_execution_id = result.execution_id
    review.completed_at = datetime.now(UTC)
    review.failure_detail = None
    session.flush()
    return SegmentReviewOutcome(review=review, finding_count=len(envelope.findings), model_called=True)


def mark_segment_review_failed(session: Session, *, review: SegmentLearningReview, error: Exception) -> None:
    """Persist a safe retryable Review failure without retaining semantic content."""

    review.status, review.output, review.ai_execution_id, review.completed_at = "FAILED", None, None, None
    review.failure_detail = _safe_failure_detail(error)
    session.flush()


def _require_supported_version(version: SegmentReviewVersion, *, provider: str, model: str) -> None:
    if (
        version.schema_version != _EXECUTABLE_REVIEW_VERSION.schema_version
        or version.prompt_version != _EXECUTABLE_REVIEW_VERSION.prompt_version
        or version.rubric_version != _EXECUTABLE_REVIEW_VERSION.rubric_version
        or version.policy_version != _EXECUTABLE_REVIEW_VERSION.policy_version
        or version.provider != provider or version.model != model
    ):
        raise UnsupportedSegmentReviewContract("UnsupportedSegmentReviewContract")


def _find_or_create_review(
    session: Session, *, learning_session: LearningSession, segment: LearningSegment,
    version: SegmentReviewVersion, provider: str, model: str,
) -> SegmentLearningReview:
    _validate_lineage(session, learning_session=learning_session, segment=segment)
    review = session.execute(
        select(SegmentLearningReview).where(
            SegmentLearningReview.segment_id == segment.id,
            SegmentLearningReview.schema_version == version.schema_version,
            SegmentLearningReview.prompt_version == version.prompt_version,
            SegmentLearningReview.rubric_version == version.rubric_version,
            SegmentLearningReview.review_policy_version == version.policy_version,
            SegmentLearningReview.provider == provider,
            SegmentLearningReview.model == model,
        ).with_for_update()
    ).scalar_one_or_none()
    if review is not None:
        return review
    review = create_segment_learning_review(
        session, student_id=learning_session.student_id, session_id=learning_session.id,
        segment_id=segment.id, schema_version=version.schema_version,
        prompt_version=version.prompt_version, rubric_version=version.rubric_version,
        review_policy_version=version.policy_version, provider=provider, model=model,
    )
    session.flush()
    return review


def _validate_lineage(session: Session, *, learning_session: LearningSession, segment: LearningSegment) -> None:
    if session.get(Student, learning_session.student_id) is None or segment.session_id != learning_session.id or segment.closed_at is None or segment.closure_reason is None:
        raise SegmentReviewLineageError("SegmentReviewLineageError")


def _complete_raw_segment(session: Session, *, learning_session: LearningSession, segment: LearningSegment) -> list[LearningMessage]:
    _validate_lineage(session, learning_session=learning_session, segment=segment)
    messages = list(session.scalars(select(LearningMessage).where(
        LearningMessage.session_id == learning_session.id,
        LearningMessage.segment_id == segment.id,
    ).order_by(LearningMessage.created_at, LearningMessage.id)))
    if not any(message.role == "student" for message in messages):
        raise SegmentReviewLineageError("SegmentReviewLineageError")
    return messages


def _candidate_source_ids(candidate: CandidateEvent) -> set[UUID]:
    payload = candidate.payload if isinstance(candidate.payload, dict) else {}
    raw_ids = payload.get("source_message_ids")
    if not isinstance(raw_ids, list):
        return set()
    try:
        return {UUID(str(value)) for value in raw_ids}
    except (TypeError, ValueError):
        return set()


def _valid_candidate_hints(session: Session, *, learning_session: LearningSession, messages: list[LearningMessage]) -> list[CandidateEvent]:
    messages_by_id = {message.id: message for message in messages}
    candidates = list(session.scalars(select(CandidateEvent).where(CandidateEvent.session_id == learning_session.id).order_by(CandidateEvent.created_at, CandidateEvent.id)))
    return [
        candidate
        for candidate in candidates
        if _is_safe_segment_candidate_hint(
            candidate,
            learning_session=learning_session,
            messages_by_id=messages_by_id,
        )
    ]


def _is_safe_segment_candidate_hint(
    candidate: CandidateEvent,
    *,
    learning_session: LearningSession,
    messages_by_id: dict[UUID, LearningMessage],
) -> bool:
    """Allow only structurally valid, optional Candidate hints into AI input."""

    payload = candidate.payload if isinstance(candidate.payload, dict) else {}
    source_ids = _candidate_source_ids(candidate)
    source = messages_by_id.get(candidate.message_id)
    if (
        candidate.session_id != learning_session.id
        or candidate.event_type not in _SUPPORTED_SEGMENT_CANDIDATE_TYPES
        or payload.get("candidate_schema_version") != CANDIDATE_EVENT_SCHEMA_VERSION
        or candidate.message_id is None
        or source is None
        or source.role != "student"
        or source_ids != {candidate.message_id}
        or any(messages_by_id.get(source_id) is None or messages_by_id[source_id].role != "student" for source_id in source_ids)
    ):
        return False
    try:
        CandidateEventMetadataItem.model_validate(
            {
                "event_type": candidate.event_type,
                "concept_ref": candidate.concept_ref,
                "summary": payload.get("summary"),
                "signal": candidate.signal,
                "source_message_ids": [str(source_id) for source_id in source_ids],
                "school_or_extended": payload.get("school_or_extended"),
                "observed_student_outcome": payload.get("observed_student_outcome"),
                "misconception_evidence": payload.get("misconception_evidence"),
            }
        )
    except ValidationError:
        return False
    if candidate.event_type == "misconception_signal":
        return _has_valid_candidate_misconception(payload, source=source, source_ids=source_ids)
    if candidate.event_type == "strategy_outcome":
        return _has_valid_candidate_strategy_outcome(
            payload,
            learning_session=learning_session,
            student_source=source,
            messages_by_id=messages_by_id,
        )
    return True


def _has_valid_candidate_misconception(
    payload: dict[str, object],
    *,
    source: LearningMessage,
    source_ids: set[UUID],
) -> bool:
    try:
        evidence = MisconceptionEvidence.model_validate(payload.get("misconception_evidence"))
    except ValidationError:
        return False
    return (
        evidence.version == MISCONCEPTION_EVIDENCE_SCHEMA_VERSION
        and evidence.source_message_id == source.id
        and evidence.source_message_id in source_ids
        and _normalize_grounding_text(evidence.explicit_student_reasoning)
        in _normalize_grounding_text(source.content)
    )


def _has_valid_candidate_strategy_outcome(
    payload: dict[str, object],
    *,
    learning_session: LearningSession,
    student_source: LearningMessage,
    messages_by_id: dict[UUID, LearningMessage],
) -> bool:
    method = is_supported_teaching_method(
        payload.get("strategy_key"),
        registry_version=payload.get("strategy_registry_version"),
    )
    if method is None or payload.get("strategy_registry_version") != TEACHING_METHOD_REGISTRY_VERSION:
        return False
    try:
        tutor_id = UUID(str(payload.get("strategy_source_tutor_message_id")))
    except (TypeError, ValueError):
        return False
    tutor = messages_by_id.get(tutor_id)
    tutor_payload = tutor.payload if tutor is not None and isinstance(tutor.payload, dict) else {}
    persisted_method = is_supported_teaching_method(
        tutor_payload.get("teaching_method_id"),
        registry_version=tutor_payload.get("teaching_method_registry_version"),
    )
    return (
        tutor is not None
        and tutor.session_id == learning_session.id
        and tutor.role == "tutor"
        and (tutor.created_at, tutor.id) < (student_source.created_at, student_source.id)
        and persisted_method is method
        and tutor_payload.get("teaching_method_registry_version") == payload.get("strategy_registry_version")
        and isinstance(payload.get("observed_student_outcome"), str)
        and bool(payload["observed_student_outcome"].strip())
    )


def _historical_anchors(
    session: Session,
    *,
    learning_session: LearningSession,
    segment: LearningSegment,
) -> list[HistoricalEvidenceAnchor]:
    """Select only prior Session-authorized same-subject demonstrations.

    These are intentionally not a history lookup. They are the smallest
    durable authority needed when a Segment Review evaluates delayed retention.
    """

    reference_time = segment.closed_at
    if reference_time is None:
        return []
    rows = session.execute(
        select(
            LearningEvidence.id,
            LearningEvent.subject,
            LearningEvidence.concept_ref,
            LearningEvidence.dimensions,
            LearningSession.closed_at,
        )
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .join(
            IntelligenceSessionAuthority,
            (
                (IntelligenceSessionAuthority.student_id == learning_session.student_id)
                & (IntelligenceSessionAuthority.session_id == LearningEvent.session_id)
                & (
                    IntelligenceSessionAuthority.evidence_processing_run_id
                    == LearningEvent.processing_run_id
                )
            ),
        )
        .join(LearningSession, LearningEvent.session_id == LearningSession.id)
        .join(
            IntelligenceProcessingRun,
            LearningEvent.processing_run_id == IntelligenceProcessingRun.id,
        )
        .where(
            LearningSession.student_id == learning_session.student_id,
            IntelligenceProcessingRun.student_id == learning_session.student_id,
            LearningEvent.session_id != learning_session.id,
            LearningEvidence.concept_ref.is_not(None),
            LearningEvidence.concept_ref == LearningEvent.concept_ref,
            LearningEvidence.dimensions["understanding"].astext.in_(
                ("demonstrated", "strong_demonstration")
            ),
            IntelligenceProcessingRun.status == "COMPLETED",
            LearningSession.closed_at.is_not(None),
            LearningSession.closed_at < reference_time,
        )
        .order_by(LearningSession.closed_at.desc(), LearningEvidence.id.desc())
        .limit(HISTORICAL_ANCHOR_LIMIT)
    ).all()
    anchors: list[HistoricalEvidenceAnchor] = []
    for evidence_id, broad_subject, concept_ref, dimensions, observed_at in rows:
        if (
            not is_supported_broad_subject(broad_subject)
            or not isinstance(concept_ref, str)
            or not isinstance(dimensions, dict)
            or not isinstance(observed_at, datetime)
        ):
            continue
        elapsed = reference_time - observed_at
        state = dimensions.get("understanding")
        if elapsed < MEANINGFUL_RETENTION_DELAY or state not in {
            "demonstrated",
            "strong_demonstration",
        }:
            continue
        anchors.append(
            HistoricalEvidenceAnchor(
                evidence_id=evidence_id,
                broad_subject=broad_subject,
                concept_ref=concept_ref,
                prior_demonstration_state=state,
                prior_observed_at=observed_at,
                elapsed_time=f"P{elapsed.days}D",
            )
        )
    return anchors


def persisted_review_historical_anchors(
    session: Session,
    *,
    learning_session: LearningSession,
    segment: LearningSegment,
    review: SegmentLearningReview,
) -> list[HistoricalEvidenceAnchor]:
    """Resolve only a completed Review's exact, durably authorized anchors.

    Fresh Review input deliberately uses `_historical_anchors`, which exposes
    only the current authority.  A persisted Review instead needs to remain
    auditable after a later complete reprocess replaces its source Session's
    current authority.  The reprocess activation audit is the narrow durable
    proof that the exact old Evidence run was formerly authorized; ordinary
    old Evidence is never sufficient.
    """

    if not isinstance(review.output, dict) or segment.closed_at is None:
        return []
    try:
        envelope = (
            SegmentLearningReviewV3Envelope.model_validate(review.output)
            if review.output.get("version") == SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
            else SegmentLearningReviewEnvelope.model_validate(review.output)
        )
    except ValidationError:
        return []
    requested_ids = {
        evidence_id
        for finding in envelope.findings
        for evidence_id in finding.historical_anchor_evidence_ids
    }
    if not requested_ids:
        return []
    review_completed_at = review.completed_at or review.created_at
    if review_completed_at is None:
        return []
    rows = session.execute(
        select(
            LearningEvidence.id,
            LearningEvent.subject,
            LearningEvidence.concept_ref,
            LearningEvidence.dimensions,
            LearningSession.closed_at,
            LearningSession.id,
            LearningEvent.processing_run_id,
        )
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .join(LearningSession, LearningEvent.session_id == LearningSession.id)
        .join(
            IntelligenceProcessingRun,
            LearningEvent.processing_run_id == IntelligenceProcessingRun.id,
        )
        .where(
            LearningEvidence.id.in_(requested_ids),
            LearningSession.student_id == learning_session.student_id,
            IntelligenceProcessingRun.student_id == learning_session.student_id,
            LearningEvent.session_id != learning_session.id,
            LearningEvidence.concept_ref.is_not(None),
            LearningEvidence.concept_ref == LearningEvent.concept_ref,
            LearningEvidence.dimensions["understanding"].astext.in_(
                ("demonstrated", "strong_demonstration")
            ),
            IntelligenceProcessingRun.status == "COMPLETED",
            LearningSession.closed_at.is_not(None),
            LearningSession.closed_at < segment.closed_at,
        )
    ).all()
    anchors: list[HistoricalEvidenceAnchor] = []
    for evidence_id, broad_subject, concept_ref, dimensions, observed_at, source_session_id, run_id in rows:
        if (
            not is_supported_broad_subject(broad_subject)
            or not isinstance(concept_ref, str)
            or not isinstance(dimensions, dict)
            or not isinstance(observed_at, datetime)
        ):
            continue
        elapsed = segment.closed_at - observed_at
        state = dimensions.get("understanding")
        if (
            elapsed < MEANINGFUL_RETENTION_DELAY
            or state not in {"demonstrated", "strong_demonstration"}
            or not _historically_authorized_evidence_run(
                session,
                student_id=learning_session.student_id,
                source_session_id=source_session_id,
                evidence_processing_run_id=run_id,
                review_completed_at=review_completed_at,
            )
        ):
            continue
        anchors.append(
            HistoricalEvidenceAnchor(
                evidence_id=evidence_id,
                broad_subject=broad_subject,
                concept_ref=concept_ref,
                prior_demonstration_state=state,
                prior_observed_at=observed_at,
                elapsed_time=f"P{elapsed.days}D",
            )
        )
    return anchors


def _historically_authorized_evidence_run(
    session: Session,
    *,
    student_id: UUID,
    source_session_id: UUID,
    evidence_processing_run_id: UUID,
    review_completed_at: datetime,
) -> bool:
    """Require current authority or a later completed reprocess audit record."""

    current_authority = session.execute(
        select(IntelligenceSessionAuthority.id).where(
            IntelligenceSessionAuthority.student_id == student_id,
            IntelligenceSessionAuthority.session_id == source_session_id,
            IntelligenceSessionAuthority.evidence_processing_run_id
            == evidence_processing_run_id,
        )
    ).scalar_one_or_none()
    if current_authority is not None:
        return True
    for reprocess in session.scalars(
        select(IntelligenceReprocessRun).where(
            IntelligenceReprocessRun.student_id == student_id,
            IntelligenceReprocessRun.status == "COMPLETED",
        )
    ):
        activation = (
            reprocess.result.get("activation")
            if isinstance(reprocess.result, dict)
            else None
        )
        if not isinstance(activation, dict) or activation.get("status") != "COMPLETED":
            continue
        activated_at = _activation_timestamp(activation.get("activated_at"))
        previous_by_session = activation.get("previous_authority_by_session")
        previous = (
            previous_by_session.get(str(source_session_id))
            if isinstance(previous_by_session, dict)
            else None
        )
        if (
            activated_at is not None
            and activated_at >= review_completed_at
            and isinstance(previous, dict)
            and previous.get("evidence_processing_run_id")
            == str(evidence_processing_run_id)
        ):
            return True
    return False


def _activation_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _model_payload(
    *,
    learning_session: LearningSession,
    segment: LearningSegment,
    messages: list[LearningMessage],
    candidates: list[CandidateEvent],
    historical_anchors: list[HistoricalEvidenceAnchor],
) -> dict[str, object]:
    candidate_hints = [{
        "candidate_id": str(candidate.id), "event_type": candidate.event_type,
        "concept_ref": candidate.concept_ref, "signal": candidate.signal,
        "summary": candidate.payload.get("summary") if isinstance(candidate.payload, dict) else None,
        "source_message_ids": [str(identifier) for identifier in _candidate_source_ids(candidate)],
        "school_or_extended": candidate.payload.get("school_or_extended") if isinstance(candidate.payload, dict) else None,
        "observed_student_outcome": candidate.payload.get("observed_student_outcome") if isinstance(candidate.payload, dict) else None,
        "misconception_evidence": candidate.payload.get("misconception_evidence") if isinstance(candidate.payload, dict) else None,
    } for candidate in candidates]
    guided_checks: list[dict[str, object]] = []
    teaching_methods: list[dict[str, object]] = []
    for tutor in (message for message in messages if message.role == "tutor"):
        metadata = tutor.payload if isinstance(tutor.payload, dict) else {}
        guided = persisted_guided_learning_check(metadata.get("guided_check"))
        if guided is not None:
            response = next((message for message in messages if message.role == "student" and isinstance(message.payload, dict) and message.payload.get("guided_check_id") == str(guided.id) and message.payload.get("guided_check_source_tutor_message_id") == str(tutor.id)), None)
            if response is not None:
                guided_checks.append({"source_tutor_message_id": str(tutor.id), "guided_check_id": str(guided.id), "prompt": guided.prompt, "choices": [choice.label for choice in guided.choices], "student_response_message_id": str(response.id), "selected_response": response.content})
        method = is_supported_teaching_method(metadata.get("teaching_method_id"), registry_version=metadata.get("teaching_method_registry_version"))
        if method is not None and metadata.get("teaching_method_registry_version") == TEACHING_METHOD_REGISTRY_VERSION:
            teaching_methods.append({"source_tutor_message_id": str(tutor.id), "teaching_method_id": method.value, "teaching_method_registry_version": TEACHING_METHOD_REGISTRY_VERSION})
    content = {
        "segment": {"student_id": str(learning_session.student_id), "session_id": str(learning_session.id), "segment_id": str(segment.id), "sequence": segment.sequence, "closed_at": segment.closed_at.isoformat() if segment.closed_at else None, "closure_reason": segment.closure_reason},
        "raw_messages": [{"id": str(message.id), "role": message.role, "content": message.content, "created_at": message.created_at.isoformat()} for message in messages],
        "candidate_hints": candidate_hints,
        "guided_learning_checks": guided_checks,
        "teaching_methods": teaching_methods,
        "historical_anchors": [anchor.model_input() for anchor in historical_anchors],
        "trusted_school_source_refs": [],
        "broad_subject_registry": {
            "version": BROAD_SUBJECT_REGISTRY_VERSION,
            "keys": list(BROAD_SUBJECT_KEYS),
        },
    }
    return {"instructions": _PROMPT, "input": json.dumps(content, sort_keys=True, separators=(",", ":")), "response_schema": SEGMENT_REVIEW_RESPONSE_SCHEMA}


_PROMPT = (
    "Review the complete supplied raw Segment only. Raw interaction outranks optional provisional Candidate hints. "
    "Classify segment_kind as LEARNING or NON_LEARNING. A LEARNING Review must select exactly one primary_broad_subject from the supplied registry and may contain Findings for different concepts only within that Subject. A NON_LEARNING Review must return findings=[] with no academic Subject. For NON_LEARNING, school_context must be null. For LEARNING, trusted_school_source_refs is authoritative: when it is empty, school_context must use school_relation=UNKNOWN and null/empty school fields; never invent school structure or source refs. reported_broad_subject must be null unless an explicit compatibility claim uses an exact supplied Broad Subject registry key equal to primary_broad_subject; it may never establish a second Subject or contain a language, topic, or domain label. "
    "Return findings=[] when no supported learning occurrence exists. Casual greetings, navigation, preferences, and Tutor explanation without observable Student outcome may have no finding. "
    "Confusion, a bare wrong answer, and an arithmetic slip are not misconception by themselves; explicit Student wrong reasoning may support one. For a misconception_signal, misconception_evidence must use version misconception-evidence-v1, cite its Student source within source_message_ids, and copy explicit_student_reasoning as an exact normalized substring of that cited Student message; never paraphrase it. If those conditions are unavailable, omit the misconception Finding. "
    "Use understanding=strong_demonstration only when reasoning_demonstration=well_supported and independence is not full_teaching; otherwise use a lower supported understanding value. "
    "When a later Student message corrects earlier reasoning, preserve both observations when supported and emit a separate self_correction Finding grounded in the correction; set self_correction to prompted or self_initiated only on that self_correction Finding. Set self_correction to not_observed on every other event type. "
    "Do not infer independence after full teaching, transfer from near-identical practice, retention without supplied anchors, or TeachingMethod identity. A retention Finding must be a retention_check, cite one or more supplied historical_anchor_evidence_ids for the same concept, and copy its concept_ref exactly from that supplied anchor (including punctuation and separators); use retention_context=meaningfully_delayed, and use relationship=retention_failure only for retrieval_failed or partial_retrieval. Without an exact supplied anchor, set retention=not_tested and historical_anchor_evidence_ids=[]. "
    "Evaluate method effectiveness only with supplied method lineage and a later Student outcome; express it only in a strategy_outcome Finding and set strategy_effectiveness to not_evaluable on every other event type. Do not emit psychological, personality, or intelligence labels, mastery percentages, or numeric confidence. "
    "Every Finding must cite exact supplied raw IDs and include at least one Student message ID; Tutor messages alone cannot support a Finding. Distinguish possible cross-subject learning."
)


def _enforce_capacity(payload: dict[str, object], *, settings: Settings | None) -> None:
    if len(json.dumps(payload, sort_keys=True, separators=(",", ":"))) > (settings or get_settings()).segment_review_context_capacity:
        raise SegmentReviewCapacityError("SEGMENT_REVIEW_CAPACITY_EXCEEDED")


def validate_segment_review_output(
    output: dict[str, object],
    *,
    messages: list[LearningMessage],
    candidates: list[CandidateEvent],
    historical_anchors: list[HistoricalEvidenceAnchor] | None = None,
) -> SegmentLearningReviewEnvelope:
    """Parse a persisted Review row, including historical v2 audit output."""

    try:
        envelope = (
            SegmentLearningReviewV3Envelope.model_validate(output)
            if output.get("version") == SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
            else SegmentLearningReviewEnvelope.model_validate(output)
        )
    except ValidationError as error:
        raise SegmentReviewValidationError("SegmentReviewValidationError") from error
    return _validate_review_findings(
        envelope,
        messages=messages,
        candidates=candidates,
        historical_anchors=historical_anchors,
    )


def validate_live_segment_review_output(
    output: dict[str, object],
    *,
    messages: list[LearningMessage],
    candidates: list[CandidateEvent],
    historical_anchors: list[HistoricalEvidenceAnchor] | None = None,
    trusted_school_source_refs: frozenset[str] = frozenset(),
) -> SegmentLearningReviewEnvelope:
    """Parse a live provider result under the executable v3-only contract."""

    try:
        envelope = SegmentLearningReviewV3Envelope.model_validate(output)
    except ValidationError as error:
        raise SegmentReviewValidationError("SegmentReviewValidationError") from error
    school_context = envelope.school_context
    if (
        school_context is not None
        and school_context.school_relation != "UNKNOWN"
        and (
            not trusted_school_source_refs
            or not set(school_context.source_refs).issubset(trusted_school_source_refs)
        )
    ):
        raise SegmentReviewValidationError("SegmentReviewValidationError")
    return _validate_review_findings(
        envelope,
        messages=messages,
        candidates=candidates,
        historical_anchors=historical_anchors,
    )


def _validate_review_findings(
    envelope: SegmentLearningReviewEnvelope,
    *,
    messages: list[LearningMessage],
    candidates: list[CandidateEvent],
    historical_anchors: list[HistoricalEvidenceAnchor] | None,
) -> SegmentLearningReviewEnvelope:
    """Apply compiled Finding checks after version-specific envelope parsing."""

    messages_by_id = {message.id: message for message in messages}
    candidates_by_id = {candidate.id: candidate for candidate in candidates}
    for finding in envelope.findings:
        _validate_finding(
            finding,
            messages_by_id=messages_by_id,
            candidates_by_id=candidates_by_id,
            historical_anchors_by_id={anchor.evidence_id: anchor for anchor in historical_anchors or []},
            primary_broad_subject=envelope.primary_broad_subject,
        )
    return envelope


def _validate_finding(
    finding: SegmentReviewFinding,
    *,
    messages_by_id: dict[UUID, LearningMessage],
    candidates_by_id: dict[UUID, CandidateEvent],
    historical_anchors_by_id: dict[UUID, HistoricalEvidenceAnchor],
    primary_broad_subject: str | None,
) -> None:
    sources = [messages_by_id.get(identifier) for identifier in finding.source_message_ids]
    if any(source is None for source in sources) or not any(source is not None and source.role == "student" for source in sources):
        raise SegmentReviewValidationError("SegmentReviewValidationError")
    if any(candidate_id not in candidates_by_id for candidate_id in finding.candidate_event_ids):
        raise SegmentReviewValidationError("SegmentReviewValidationError")
    _validate_retention(
        finding,
        historical_anchors_by_id=historical_anchors_by_id,
        primary_broad_subject=primary_broad_subject,
    )
    if finding.dimensions.transfer != "not_tested" and (finding.validated_event_type != "transfer_attempt" or finding.transfer_context != "meaningfully_changed"):
        raise SegmentReviewValidationError("SegmentReviewValidationError")
    if finding.dimensions.self_correction != "not_observed" and finding.validated_event_type != "self_correction":
        raise SegmentReviewValidationError("SegmentReviewValidationError")
    if finding.dimensions.understanding == "strong_demonstration" and (finding.dimensions.reasoning_demonstration != "well_supported" or finding.dimensions.independence == "full_teaching"):
        raise SegmentReviewValidationError("SegmentReviewValidationError")
    _validate_misconception(finding, messages_by_id=messages_by_id)
    _validate_teaching_method(finding, messages_by_id=messages_by_id)
    if finding.dimensions.strategy_effectiveness != "not_evaluable":
        tutor = messages_by_id.get(finding.teaching_method_source_tutor_message_id) if finding.teaching_method_source_tutor_message_id else None
        if finding.validated_event_type != "strategy_outcome" or tutor is None or not any(source is not None and source.role == "student" and (source.created_at, source.id) > (tutor.created_at, tutor.id) for source in sources):
            raise SegmentReviewValidationError("SegmentReviewValidationError")


def _validate_retention(
    finding: SegmentReviewFinding,
    *,
    historical_anchors_by_id: dict[UUID, HistoricalEvidenceAnchor],
    primary_broad_subject: str | None,
) -> None:
    tested = finding.dimensions.retention != "not_tested"
    if not tested:
        if (
            finding.retention_context != "not_tested"
            or finding.historical_anchor_evidence_ids
            or finding.relationship == "retention_failure"
        ):
            raise SegmentReviewValidationError("SegmentReviewValidationError")
        return
    anchors = [historical_anchors_by_id.get(identifier) for identifier in finding.historical_anchor_evidence_ids]
    if (
        finding.validated_event_type != "retention_check"
        or finding.retention_context != "meaningfully_delayed"
        or finding.concept_ref is None
        or not anchors
        or any(anchor is None or anchor.concept_ref != finding.concept_ref for anchor in anchors)
        or any(anchor is None or anchor.broad_subject != primary_broad_subject for anchor in anchors)
        or any(_duration_days(anchor.elapsed_time) < MEANINGFUL_RETENTION_DELAY.days for anchor in anchors if anchor is not None)
    ):
        raise SegmentReviewValidationError("SegmentReviewValidationError")
    failed_retrieval = finding.dimensions.retention in {"retrieval_failed", "partial_retrieval"}
    if failed_retrieval != (finding.relationship == "retention_failure"):
        raise SegmentReviewValidationError("SegmentReviewValidationError")


def _duration_days(value: str) -> int:
    if not value.startswith("P") or not value.endswith("D"):
        return -1
    try:
        return int(value[1:-1])
    except ValueError:
        return -1


def _validate_misconception(finding: SegmentReviewFinding, *, messages_by_id: dict[UUID, LearningMessage]) -> None:
    if finding.validated_event_type != "misconception_signal":
        return
    evidence = finding.misconception_evidence
    if evidence is None or evidence.version != MISCONCEPTION_EVIDENCE_SCHEMA_VERSION or evidence.source_message_id not in finding.source_message_ids:
        raise SegmentReviewValidationError("SegmentReviewValidationError")
    source = messages_by_id.get(evidence.source_message_id)
    if source is None or source.role != "student" or _normalize_grounding_text(evidence.explicit_student_reasoning) not in _normalize_grounding_text(source.content):
        raise SegmentReviewValidationError("SegmentReviewValidationError")


def _validate_teaching_method(finding: SegmentReviewFinding, *, messages_by_id: dict[UUID, LearningMessage]) -> None:
    if (finding.teaching_method_id is None) != (finding.teaching_method_source_tutor_message_id is None):
        raise SegmentReviewValidationError("SegmentReviewValidationError")
    if finding.teaching_method_id is None:
        return
    source = messages_by_id.get(finding.teaching_method_source_tutor_message_id)
    payload = source.payload if source is not None and isinstance(source.payload, dict) else {}
    method = is_supported_teaching_method(payload.get("teaching_method_id"), registry_version=payload.get("teaching_method_registry_version"))
    if source is None or source.role != "tutor" or method is not finding.teaching_method_id:
        raise SegmentReviewValidationError("SegmentReviewValidationError")


def _normalize_grounding_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def _finding_count(review: SegmentLearningReview) -> int:
    findings = review.output.get("findings") if isinstance(review.output, dict) else None
    return len(findings) if isinstance(findings, list) else 0


def _safe_failure_detail(error: Exception) -> str:
    if isinstance(error, SegmentReviewCapacityError):
        return "SEGMENT_REVIEW_CAPACITY_EXCEEDED"
    if isinstance(error, SegmentReviewLineageError):
        return "SegmentReviewLineageError"
    if isinstance(error, UnsupportedSegmentReviewContract):
        return "UnsupportedSegmentReviewContract"
    if isinstance(error, SegmentReviewProviderError):
        return "SegmentReviewProviderError"
    return "SegmentReviewValidationError"
