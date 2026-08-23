"""Source-grounded, versioned Session Evidence consolidation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.db.models import (
    CandidateEvent,
    IntelligenceProcessingRun,
    LearningEvidence,
    LearningEvent,
    LearningMessage,
    LearningSession,
    ModelTask,
)
from services.tutor.candidate_events import HistoricalCandidateEventType
from services.tutor.teaching_methods import (
    TEACHING_METHOD_REGISTRY_VERSION,
    is_supported_teaching_method,
)


SESSION_EVIDENCE_SCHEMA_VERSION = "session-evidence-v1"
SESSION_EVIDENCE_PROMPT_VERSION = "session-evidence-prompt-v2"
EVIDENCE_RUBRIC_VERSION = "evidence-rubric-v1"
SESSION_CONSOLIDATION_POLICY_VERSION = "session-consolidation-policy-v1"

Understanding = Literal[
    "not_observed",
    "not_demonstrated",
    "partial",
    "demonstrated",
    "strong_demonstration",
]
Independence = Literal[
    "independent",
    "light_support",
    "moderate_support",
    "substantial_support",
    "full_teaching",
    "not_applicable",
]
Reasoning = Literal["not_observed", "fragmented", "coherent", "well_supported"]
Transfer = Literal["not_tested", "unsuccessful", "partial", "demonstrated"]
SelfCorrection = Literal["not_observed", "externally_corrected", "prompted", "self_initiated"]
Retention = Literal[
    "not_tested",
    "retrieval_failed",
    "partial_retrieval",
    "retained",
    "rapid_recovery",
]
StrategyEffectiveness = Literal[
    "not_evaluable",
    "ineffective",
    "unclear",
    "helped",
    "enabled_independent_success",
]
Persistence = Literal[
    "not_observed",
    "stopped",
    "continued_with_support",
    "continued_independently",
]
ConfidenceCalibration = Literal[
    "not_observed",
    "under_confident",
    "calibrated",
    "over_confident",
]
EvidenceRelationship = Literal[
    "supports",
    "contradicts",
    "improvement",
    "retention_failure",
    "scope_exception",
    "insufficient",
    "unrelated",
]


class EvidenceDimensions(BaseModel):
    """All approved contextual evidence dimensions, never numeric learner scores."""

    model_config = ConfigDict(extra="forbid")

    understanding: Understanding
    independence: Independence
    reasoning_demonstration: Reasoning
    transfer: Transfer
    self_correction: SelfCorrection
    retention: Retention
    strategy_effectiveness: StrategyEffectiveness
    persistence: Persistence
    confidence_calibration: ConfidenceCalibration


class ConsolidatedEvent(BaseModel):
    """One candidate-grounded contextual event proposed by consolidation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    candidate_event_id: UUID
    source_message_ids: list[UUID] = Field(min_length=1, max_length=4)
    subject: str = Field(min_length=1, max_length=32)
    concept_ref: str | None = Field(default=None, min_length=1, max_length=128)
    event_type: HistoricalCandidateEventType
    event_summary: str = Field(min_length=1, max_length=800)
    school_or_extended: Literal["school", "extended"]
    transfer_context: Literal["not_tested", "near_identical", "meaningfully_changed"] = "not_tested"
    retention_context: Literal["not_tested", "immediate", "meaningfully_delayed"] = "not_tested"
    dimensions: EvidenceDimensions
    relationship: EvidenceRelationship

    @model_validator(mode="after")
    def reject_unsupported_learner_labels(self) -> "ConsolidatedEvent":
        lowered = self.event_summary.lower()
        forbidden = (
            "visual learner",
            "learning style",
            "highly intelligent",
            "poor attention",
            "careless",
            "low motivation",
            "personality",
        )
        if any(label in lowered for label in forbidden):
            raise ValueError("Event summary contains an unsupported learner label.")
        return self


class SessionEvidenceEnvelope(BaseModel):
    """The only persisted interpretation shape accepted from the model."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[SESSION_EVIDENCE_SCHEMA_VERSION]
    events: list[ConsolidatedEvent] = Field(max_length=12)

    @model_validator(mode="after")
    def require_each_candidate_to_produce_at_most_one_event(self) -> "SessionEvidenceEnvelope":
        candidate_ids = [event.candidate_event_id for event in self.events]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("A Candidate Event may produce at most one validated event per run.")
        return self


SESSION_EVIDENCE_RESPONSE_SCHEMA: dict[str, object] = {
    "name": "session_evidence_v1",
    "schema": SessionEvidenceEnvelope.model_json_schema(),
}


class ConsolidationError(RuntimeError):
    """A closed session cannot safely be consolidated under this contract."""


class ConsolidationValidationError(ConsolidationError):
    """Model output does not have enough source-grounded support to persist."""


class EvidenceContractError(ConsolidationError):
    """A requested Evidence identity has no executable parser/prompt contract."""


@dataclass(frozen=True)
class ConsolidationOutcome:
    processing_run: IntelligenceProcessingRun
    event_count: int
    model_called: bool


@dataclass(frozen=True)
class ConsolidationVersion:
    """Explicit, auditable interpretation identity for a session rebuild."""

    schema_version: str = SESSION_EVIDENCE_SCHEMA_VERSION
    prompt_version: str = SESSION_EVIDENCE_PROMPT_VERSION
    rubric_version: str = EVIDENCE_RUBRIC_VERSION
    policy_version: str = SESSION_CONSOLIDATION_POLICY_VERSION
    provider: str | None = None
    model: str | None = None


_EXECUTABLE_CONSOLIDATION_VERSION = ConsolidationVersion()


def require_supported_consolidation_version(version: ConsolidationVersion) -> None:
    """Reject metadata-only identities; only compiled contracts may be recorded."""

    executable = (
        version.schema_version == _EXECUTABLE_CONSOLIDATION_VERSION.schema_version
        and version.prompt_version == _EXECUTABLE_CONSOLIDATION_VERSION.prompt_version
        and version.rubric_version == _EXECUTABLE_CONSOLIDATION_VERSION.rubric_version
        and version.policy_version == _EXECUTABLE_CONSOLIDATION_VERSION.policy_version
    )
    if not executable:
        raise EvidenceContractError("Evidence interpretation is not an executable registered contract.")


def consolidate_closed_session(
    session: Session,
    *,
    learning_session: LearningSession,
    gateway: ModelGateway,
    version: ConsolidationVersion | None = None,
) -> ConsolidationOutcome:
    """Create validated Event/Evidence rows for one closed session only."""

    if learning_session.status != "CLOSED":
        raise ConsolidationError("Only CLOSED sessions are eligible for consolidation.")

    route = gateway.route_for(ModelTask.SESSION_EVIDENCE)
    selected_version = version or _default_consolidation_version()
    require_supported_consolidation_version(selected_version)
    if selected_version.provider is not None and selected_version.provider != route.provider:
        raise ConsolidationError("Selected evidence provider does not match the configured Gateway route.")
    if selected_version.model is not None and selected_version.model != route.model:
        raise ConsolidationError("Selected evidence model does not match the configured Gateway route.")
    run = _find_or_create_run(
        session,
        learning_session=learning_session,
        route=route,
        version=selected_version,
    )
    if run.status == "COMPLETED":
        return ConsolidationOutcome(
            processing_run=run,
            event_count=_event_count(session, run_id=run.id),
            model_called=False,
        )
    run.status = "RUNNING"
    session.flush()

    candidates = _valid_candidates(session, learning_session=learning_session)
    if not candidates:
        run.status = "COMPLETED"
        session.flush()
        return ConsolidationOutcome(processing_run=run, event_count=0, model_called=False)

    messages = _relevant_messages(session, learning_session=learning_session, candidates=candidates)
    try:
        result = gateway.execute(
            ModelTask.SESSION_EVIDENCE,
            _model_payload(
                learning_session=learning_session,
                candidates=candidates,
                messages=messages,
            ),
            lineage=AIExecutionLineage(
                operation="session_evidence_consolidation",
                operation_id=uuid5(
                    NAMESPACE_URL, f"intelligence-processing-run:{run.id}"
                ),
                student_id=learning_session.student_id,
                learning_session_id=learning_session.id,
                intelligence_processing_run_id=run.id,
                source_candidate_event_ids=tuple(candidate.id for candidate in candidates),
            ),
        )
        envelope = _parse_and_validate_output(
            result.output,
            session=session,
            learning_session=learning_session,
            candidates=candidates,
        )
    except Exception as error:
        mark_consolidation_failed(session, processing_run=run, error=error)
        raise
    _persist_output(
        session,
        run=run,
        learning_session=learning_session,
        envelope=envelope,
    )
    run.status = "COMPLETED"
    session.flush()
    return ConsolidationOutcome(
        processing_run=run,
        event_count=len(envelope.events),
        model_called=True,
    )


def mark_consolidation_failed(
    session: Session,
    *,
    processing_run: IntelligenceProcessingRun,
    error: Exception,
) -> None:
    """Retain a retryable processing-run failure without creating intelligence."""

    scope = dict(processing_run.scope)
    scope["failure_code"] = type(error).__name__
    processing_run.scope = scope
    processing_run.status = "FAILED"
    session.flush()


def _default_consolidation_version() -> ConsolidationVersion:
    """Return the identity of the parser/prompt contract compiled into this process."""

    return _EXECUTABLE_CONSOLIDATION_VERSION


def _find_or_create_run(
    session: Session,
    *,
    learning_session: LearningSession,
    route: object,
    version: ConsolidationVersion,
) -> IntelligenceProcessingRun:
    existing = session.execute(
        select(IntelligenceProcessingRun)
        .where(
            IntelligenceProcessingRun.student_id == learning_session.student_id,
            IntelligenceProcessingRun.rubric_version == version.rubric_version,
            IntelligenceProcessingRun.policy_version == version.policy_version,
            IntelligenceProcessingRun.scope["session_id"].astext == str(learning_session.id),
            IntelligenceProcessingRun.scope["consolidation_schema_version"].astext
            == version.schema_version,
            IntelligenceProcessingRun.scope["prompt_version"].astext
            == version.prompt_version,
            IntelligenceProcessingRun.scope["provider"].astext == getattr(route, "provider"),
            IntelligenceProcessingRun.scope["model"].astext == getattr(route, "model"),
        )
        .with_for_update()
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    provider = getattr(route, "provider")
    model = getattr(route, "model")
    run = IntelligenceProcessingRun(
        student_id=learning_session.student_id,
        rubric_version=version.rubric_version,
        policy_version=version.policy_version,
        status="RUNNING",
        scope={
            "session_id": str(learning_session.id),
            "consolidation_schema_version": version.schema_version,
            "prompt_version": version.prompt_version,
            "provider": provider,
            "model": model,
        },
    )
    session.add(run)
    session.flush()
    return run


def _valid_candidates(
    session: Session,
    *,
    learning_session: LearningSession,
) -> list[CandidateEvent]:
    candidates = list(
        session.execute(
            select(CandidateEvent)
            .where(
                CandidateEvent.session_id == learning_session.id,
                CandidateEvent.message_id.is_not(None),
            )
            .order_by(CandidateEvent.created_at, CandidateEvent.id)
            .limit(12)
        ).scalars()
    )
    if not candidates:
        return []
    message_ids = {candidate.message_id for candidate in candidates if candidate.message_id is not None}
    source_messages = {
        message.id: message
        for message in session.execute(
            select(LearningMessage).where(
                LearningMessage.session_id == learning_session.id,
                LearningMessage.id.in_(message_ids),
            )
        ).scalars()
    }
    return [
        candidate
        for candidate in candidates
        if candidate.message_id in source_messages
        and source_messages[candidate.message_id].role == "student"
        and _candidate_sources(candidate) == {candidate.message_id}
        and _has_valid_strategy_outcome_lineage(
            session,
            learning_session=learning_session,
            candidate=candidate,
        )
    ]


def _candidate_sources(candidate: CandidateEvent) -> set[UUID]:
    raw_ids = candidate.payload.get("source_message_ids")
    if not isinstance(raw_ids, list):
        return set()
    try:
        return {UUID(str(value)) for value in raw_ids}
    except (TypeError, ValueError):
        return set()


def _relevant_messages(
    session: Session,
    *,
    learning_session: LearningSession,
    candidates: list[CandidateEvent],
) -> list[LearningMessage]:
    messages = list(
        session.execute(
            select(LearningMessage)
            .where(LearningMessage.session_id == learning_session.id)
            .order_by(LearningMessage.created_at, LearningMessage.id)
        ).scalars()
    )
    source_ids = {candidate.message_id for candidate in candidates}
    lineage_tutor_ids = {
        UUID(str(candidate.payload["strategy_source_tutor_message_id"]))
        for candidate in candidates
        if candidate.event_type == "strategy_outcome"
    }
    selected_ids: set[UUID] = set(lineage_tutor_ids)
    for index, message in enumerate(messages):
        if message.id not in source_ids:
            continue
        selected_ids.add(message.id)
        if index + 1 < len(messages) and messages[index + 1].role == "tutor":
            selected_ids.add(messages[index + 1].id)
    return [message for message in messages if message.id in selected_ids]


def _model_payload(
    *,
    learning_session: LearningSession,
    candidates: list[CandidateEvent],
    messages: list[LearningMessage],
) -> dict[str, object]:
    candidate_records = []
    for candidate in candidates:
        record: dict[str, object] = {
            "id": str(candidate.id),
            "event_type": candidate.event_type,
            "concept_ref": candidate.concept_ref,
            "signal": candidate.signal,
            "summary": candidate.payload.get("summary"),
            "source_message_ids": [str(identifier) for identifier in _candidate_sources(candidate)],
            "school_or_extended": candidate.payload.get("school_or_extended"),
        }
        if candidate.event_type == "strategy_outcome":
            record.update({
                "strategy_key": candidate.payload.get("strategy_key"),
                "strategy_source_tutor_message_id": candidate.payload.get("strategy_source_tutor_message_id"),
                "strategy_registry_version": candidate.payload.get("strategy_registry_version"),
                "observed_student_outcome": candidate.payload.get("observed_student_outcome"),
            })
        candidate_records.append(record)
    excerpts = [
        {
            "id": str(message.id),
            "role": message.role,
            "content": message.content,
        }
        for message in messages
    ]
    return {
        "instructions": (
            "Interpret only the supplied raw session excerpts and Candidate Events. "
            "Candidates are hints, not truth. Return no event when support is insufficient. "
            "Use every categorical rubric dimension exactly as defined. Do not infer "
            "independence after full teaching, transfer from near-identical practice, "
            "retention without meaningful delay, or strategy effectiveness without an "
            "observable Student outcome. For strategy outcomes, the supplied method lineage is server-grounded context: interpret effectiveness only and never choose or rename the method. Never produce mastery, numeric confidence, or learner labels."
        ),
        "input": json.dumps(
            {
                "session_id": str(learning_session.id),
                "subject": learning_session.subject,
                "candidates": candidate_records,
                "relevant_excerpts": excerpts,
            }
        ),
        "response_schema": SESSION_EVIDENCE_RESPONSE_SCHEMA,
    }


def _parse_and_validate_output(
    output: dict[str, object],
    *,
    session: Session,
    learning_session: LearningSession,
    candidates: list[CandidateEvent],
) -> SessionEvidenceEnvelope:
    try:
        envelope = SessionEvidenceEnvelope.model_validate(output)
    except ValidationError as error:
        raise ConsolidationValidationError("Session evidence output violates the contract.") from error

    candidate_by_id = {candidate.id: candidate for candidate in candidates}
    for event in envelope.events:
        candidate = candidate_by_id.get(event.candidate_event_id)
        if candidate is None:
            raise ConsolidationValidationError("Output references a Candidate Event outside this session.")
        if event.subject != learning_session.subject:
            raise ConsolidationValidationError("Output subject does not match the source session.")
        if candidate.concept_ref is not None and event.concept_ref != candidate.concept_ref:
            raise ConsolidationValidationError("Output concept does not match the Candidate Event.")
        if set(event.source_message_ids) != _candidate_sources(candidate):
            raise ConsolidationValidationError("Output source messages do not match the Candidate Event.")
        candidate_scope = candidate.payload.get("school_or_extended")
        if event.school_or_extended != candidate_scope:
            raise ConsolidationValidationError("Output scope does not match the Candidate Event.")
        _validate_inference_boundaries(
            session,
            learning_session=learning_session,
            candidate=candidate,
            event=event,
        )
    return envelope


def _validate_inference_boundaries(
    session: Session,
    *,
    learning_session: LearningSession,
    candidate: CandidateEvent,
    event: ConsolidatedEvent,
) -> None:
    dimensions = event.dimensions
    if candidate.event_type == "guided_success" and dimensions.independence == "independent":
        raise ConsolidationValidationError("Guided success cannot be persisted as independent success.")
    if dimensions.understanding == "strong_demonstration" and (
        dimensions.reasoning_demonstration != "well_supported"
        or dimensions.independence == "full_teaching"
    ):
        raise ConsolidationValidationError("Strong understanding needs supported reasoning without full teaching.")
    if dimensions.transfer != "not_tested" and (
        candidate.event_type != "transfer_attempt"
        or event.transfer_context != "meaningfully_changed"
    ):
        raise ConsolidationValidationError("Transfer needs a meaningful context change.")
    if dimensions.retention != "not_tested" and (
        candidate.event_type != "retention_check"
        or event.retention_context != "meaningfully_delayed"
        or not _has_meaningful_prior_concept_evidence(
            session,
            learning_session=learning_session,
            candidate=candidate,
        )
    ):
        raise ConsolidationValidationError("Retention needs a meaningful delayed prior context.")
    if dimensions.strategy_effectiveness != "not_evaluable" and (
        candidate.event_type != "strategy_outcome"
        or not isinstance(candidate.payload.get("observed_student_outcome"), str)
        or not _has_valid_strategy_outcome_lineage(
            session,
            learning_session=learning_session,
            candidate=candidate,
        )
    ):
        raise ConsolidationValidationError("Strategy effectiveness needs an observable Student outcome.")
    if dimensions.self_correction != "not_observed" and candidate.event_type != "self_correction":
        raise ConsolidationValidationError("Self-correction evidence needs a self-correction Candidate Event.")


def _has_valid_strategy_outcome_lineage(
    session: Session,
    *,
    learning_session: LearningSession,
    candidate: CandidateEvent,
) -> bool:
    """Accept method effectiveness only when runtime-attached lineage still resolves."""

    if candidate.event_type != "strategy_outcome":
        return True
    payload = candidate.payload if isinstance(candidate.payload, dict) else {}
    method = is_supported_teaching_method(
        payload.get("strategy_key"),
        registry_version=payload.get("strategy_registry_version"),
    )
    if method is None or payload.get("strategy_registry_version") != TEACHING_METHOD_REGISTRY_VERSION:
        return False
    try:
        tutor_message_id = UUID(str(payload.get("strategy_source_tutor_message_id")))
    except (TypeError, ValueError):
        return False
    tutor_message = session.get(LearningMessage, tutor_message_id)
    source_message = session.get(LearningMessage, candidate.message_id)
    if tutor_message is None or source_message is None:
        return False
    tutor_payload = tutor_message.payload if isinstance(tutor_message.payload, dict) else {}
    persisted_method = is_supported_teaching_method(
        tutor_payload.get("teaching_method_id"),
        registry_version=tutor_payload.get("teaching_method_registry_version"),
    )
    return (
        tutor_message.session_id == learning_session.id
        and source_message.session_id == learning_session.id
        and tutor_message.role == "tutor"
        and tutor_message.created_at < source_message.created_at
        and persisted_method is method
        and tutor_payload.get("teaching_method_registry_version") == payload.get("strategy_registry_version")
        and isinstance(payload.get("observed_student_outcome"), str)
    )


def _has_meaningful_prior_concept_evidence(
    session: Session,
    *,
    learning_session: LearningSession,
    candidate: CandidateEvent,
) -> bool:
    if candidate.concept_ref is None:
        return False
    prior = session.execute(
        select(LearningSession.closed_at)
        .select_from(LearningEvidence)
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .join(
            IntelligenceProcessingRun,
            LearningEvent.processing_run_id == IntelligenceProcessingRun.id,
        )
        .join(LearningSession, LearningEvent.session_id == LearningSession.id)
        .where(
            LearningSession.student_id == learning_session.student_id,
            LearningEvent.session_id != learning_session.id,
            LearningEvent.subject == learning_session.subject,
            LearningEvent.concept_ref == candidate.concept_ref,
            LearningEvidence.concept_ref == candidate.concept_ref,
            LearningEvidence.dimensions["understanding"].astext.in_(
                ("demonstrated", "strong_demonstration")
            ),
            IntelligenceProcessingRun.status == "COMPLETED",
            LearningSession.closed_at.is_not(None),
            LearningSession.closed_at < candidate.created_at,
        )
        .order_by(LearningSession.closed_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return prior is not None and candidate.created_at - prior >= timedelta(days=7)


def _persist_output(
    session: Session,
    *,
    run: IntelligenceProcessingRun,
    learning_session: LearningSession,
    envelope: SessionEvidenceEnvelope,
) -> None:
    for item in envelope.events:
        source_message_id = item.source_message_ids[0]
        event = LearningEvent(
            processing_run_id=run.id,
            session_id=learning_session.id,
            candidate_event_id=item.candidate_event_id,
            subject=item.subject,
            concept_ref=item.concept_ref,
            event_type=item.event_type,
            description=item.event_summary,
            source_message_id=source_message_id,
        )
        session.add(event)
        session.flush()
        session.add(
            LearningEvidence(
                event_id=event.id,
                concept_ref=item.concept_ref,
                dimensions=item.dimensions.model_dump(),
                relationship=item.relationship,
                source_ref=(
                    f"session:{learning_session.id}:candidate:{item.candidate_event_id}:"
                    f"message:{source_message_id}"
                ),
            )
        )
    session.flush()


def _event_count(session: Session, *, run_id: UUID) -> int:
    return len(
        session.execute(
            select(LearningEvent.id).where(LearningEvent.processing_run_id == run_id)
        ).scalars().all()
    )
