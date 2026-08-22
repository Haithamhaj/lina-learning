"""Deterministic, evidence-driven Current Learning State lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import (
    CandidateEvent,
    CurrentLearningState,
    IntelligenceProcessingRun,
    LearningEvidence,
    LearningEvent,
    LearningSession,
)


CURRENT_STATE_POLICY_VERSION = "current-state-policy-v1"
SUPPORTED_CURRENT_STATE_POLICY_VERSIONS = frozenset({CURRENT_STATE_POLICY_VERSION})
_SHORT_LIVED_STATE_WINDOWS = {
    "recent_strategy_success": timedelta(days=14),
    "recent_strategy_failure": timedelta(days=14),
    "current_school_focus": timedelta(days=7),
    "important_recent_change": timedelta(days=14),
}


class CurrentStateSourceError(ValueError):
    """The supplied Evidence is not a completed TASK-021 output."""


class CurrentStatePolicyError(ValueError):
    """A requested Current State policy has no executable implementation."""


def apply_evidence_to_current_state(
    session: Session,
    *,
    evidence_id: UUID,
    now: datetime | None = None,
    policy_version: str | None = None,
    force_derivation: bool = False,
) -> list[CurrentLearningState]:
    """Apply one validated Evidence item without creating Patterns or decision views."""

    policy_version = policy_version or CURRENT_STATE_POLICY_VERSION
    _require_supported_policy(policy_version)
    effective_now = now or datetime.now(UTC)
    evidence, event, learning_session, run = _load_validated_evidence(session, evidence_id=evidence_id)
    existing = _states_for_evidence(session, evidence_id=evidence.id, policy_version=policy_version)
    if existing and not force_derivation:
        return existing

    dimensions = evidence.dimensions
    if _independent_demonstration(dimensions):
        touched = _resolve_states(
            session,
            student_id=learning_session.student_id,
            subject=event.subject,
            concept_ref=event.concept_ref,
            state_types=("active_difficulty", "active_misconception", "open_learning_loop"),
            evidence_id=evidence.id,
            now=effective_now,
            policy_version=policy_version,
        )
    elif _partial_improvement(dimensions, evidence.relationship):
        touched = _mark_states_resolving(
            session,
            student_id=learning_session.student_id,
            subject=event.subject,
            concept_ref=event.concept_ref,
            state_types=("active_difficulty", "active_misconception", "open_learning_loop"),
            evidence_id=evidence.id,
            now=effective_now,
            policy_version=policy_version,
        )
    else:
        touched = []

    if dimensions.get("retention") in {"retained", "rapid_recovery"}:
        touched.extend(
            _resolve_states(
                session,
                student_id=learning_session.student_id,
                subject=event.subject,
                concept_ref=event.concept_ref,
                state_types=("current_retention_concern",),
                evidence_id=evidence.id,
                now=effective_now,
                policy_version=policy_version,
            )
        )

    for state_type, detail in _state_proposals(event=event, evidence=evidence):
        state = _upsert_active_state(
            session,
            student_id=learning_session.student_id,
            subject=event.subject,
            concept_ref=event.concept_ref,
            processing_run_id=run.id,
            state_type=state_type,
            detail=detail,
            evidence_id=evidence.id,
            now=effective_now,
            policy_version=policy_version,
        )
        if state not in touched:
            touched.append(state)
    session.flush()
    return touched


def rebuild_authoritative_current_states(
    session: Session,
    *,
    student_id: UUID,
    now: datetime,
    policy_version: str | None = None,
) -> list[CurrentLearningState]:
    """Replace runtime State with a fresh derivation of authoritative Evidence.

    Existing rows are retained as historical output, but no longer remain active
    merely because a replacement interpretation emitted no counter-Evidence.
    """

    from services.intelligence.authority import authoritative_evidence_ids

    policy_version = policy_version or CURRENT_STATE_POLICY_VERSION
    _require_supported_policy(policy_version)
    for state in session.execute(
        select(CurrentLearningState).where(
            CurrentLearningState.student_id == student_id,
            CurrentLearningState.policy_version == policy_version,
            CurrentLearningState.status.in_(("ACTIVE", "RESOLVING")),
        )
    ).scalars():
        state.status = "SUPERSEDED"
        state.resolved_at = now
        state.updated_at = now

    evidence_ids = authoritative_evidence_ids(session, student_id=student_id)
    if not evidence_ids:
        session.flush()
        return []
    ordered_evidence = session.execute(
        select(LearningEvidence.id, LearningSession, CandidateEvent)
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .join(CandidateEvent, LearningEvent.candidate_event_id == CandidateEvent.id)
        .join(LearningSession, LearningEvent.session_id == LearningSession.id)
        .where(LearningEvidence.id.in_(evidence_ids))
        .order_by(CandidateEvent.created_at, LearningEvent.id)
    ).all()
    rebuilt: list[CurrentLearningState] = []
    for evidence_id, learning_session, candidate in ordered_evidence:
        for state in apply_evidence_to_current_state(
            session,
            evidence_id=evidence_id,
            now=learning_session.closed_at or candidate.created_at or now,
            policy_version=policy_version,
            force_derivation=True,
        ):
            if state not in rebuilt:
                rebuilt.append(state)
    session.flush()
    return rebuilt


def apply_processing_run_current_state(
    session: Session,
    *,
    processing_run_id: UUID,
    now: datetime | None = None,
    policy_version: str | None = None,
) -> list[CurrentLearningState]:
    """Idempotently derive state for every validated Evidence item in one completed run."""

    policy_version = policy_version or CURRENT_STATE_POLICY_VERSION
    _require_supported_policy(policy_version)
    evidence_ids = session.execute(
        select(LearningEvidence.id)
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .join(CandidateEvent, LearningEvent.candidate_event_id == CandidateEvent.id)
        .where(LearningEvent.processing_run_id == processing_run_id)
        .order_by(CandidateEvent.created_at, LearningEvent.id)
    ).scalars()
    states: list[CurrentLearningState] = []
    for evidence_id in evidence_ids:
        for state in apply_evidence_to_current_state(
            session,
            evidence_id=evidence_id,
            now=now,
            policy_version=policy_version,
        ):
            if state not in states:
                states.append(state)
    return states


def expire_current_states(session: Session, *, now: datetime | None = None) -> int:
    """Move short-lived ACTIVE/RESOLVING states into historical expiry."""

    effective_now = now or datetime.now(UTC)
    states = session.execute(
        select(CurrentLearningState).where(
            CurrentLearningState.policy_version == CURRENT_STATE_POLICY_VERSION,
            CurrentLearningState.status.in_(("ACTIVE", "RESOLVING")),
            CurrentLearningState.expires_at.is_not(None),
            CurrentLearningState.expires_at <= effective_now,
        )
    ).scalars()
    count = 0
    for state in states:
        state.status = "EXPIRED"
        state.updated_at = effective_now
        count += 1
    session.flush()
    return count


def _load_validated_evidence(
    session: Session,
    *,
    evidence_id: UUID,
) -> tuple[LearningEvidence, LearningEvent, LearningSession, IntelligenceProcessingRun]:
    row = session.execute(
        select(LearningEvidence, LearningEvent, LearningSession, IntelligenceProcessingRun)
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .join(LearningSession, LearningEvent.session_id == LearningSession.id)
        .join(IntelligenceProcessingRun, LearningEvent.processing_run_id == IntelligenceProcessingRun.id)
        .where(LearningEvidence.id == evidence_id)
    ).one_or_none()
    if row is None:
        raise CurrentStateSourceError("Evidence does not exist.")
    evidence, event, learning_session, run = row
    scope = run.scope if isinstance(run.scope, dict) else {}
    if (
        run.status != "COMPLETED"
        or learning_session.status != "CLOSED"
        or not _supported_evidence_schema(scope.get("consolidation_schema_version"))
        or scope.get("session_id") != str(event.session_id)
        or evidence.concept_ref != event.concept_ref
    ):
        raise CurrentStateSourceError("Current State requires completed, validated TASK-021 Evidence.")
    return evidence, event, learning_session, run


def _supported_evidence_schema(value: object) -> bool:
    """Allow explicitly versioned TASK-021 contracts during a bounded rebuild."""

    return isinstance(value, str) and value.startswith("session-evidence-")


def _require_supported_policy(policy_version: str) -> None:
    if policy_version not in SUPPORTED_CURRENT_STATE_POLICY_VERSIONS and policy_version != CURRENT_STATE_POLICY_VERSION:
        raise CurrentStatePolicyError(f"Current State policy {policy_version!r} is not executable.")


def require_supported_current_state_policy(policy_version: str) -> None:
    """Validate a requested policy before a durable reprocess request is queued."""

    _require_supported_policy(policy_version)


def _states_for_evidence(session: Session, *, evidence_id: UUID, policy_version: str) -> list[CurrentLearningState]:
    return list(
        session.execute(
            select(CurrentLearningState).where(
                CurrentLearningState.policy_version == policy_version,
                CurrentLearningState.evidence_refs.contains([str(evidence_id)]),
            )
        ).scalars()
    )


def _state_proposals(*, event: LearningEvent, evidence: LearningEvidence) -> list[tuple[str, str]]:
    dimensions = evidence.dimensions
    understanding = dimensions.get("understanding")
    independence = dimensions.get("independence")
    proposals: list[tuple[str, str]] = []
    if understanding in {"not_demonstrated", "partial"} or independence in {
        "substantial_support",
        "full_teaching",
    }:
        proposals.append(("active_difficulty", "Recent validated evidence shows this concept currently needs support."))
    if event.event_type == "misconception_signal":
        proposals.append(("active_misconception", "Recent validated evidence shows a concept-specific misconception to revisit."))
    if event.event_type in {
        "open_loop_created",
        "learning_attempt",
        "incorrect_attempt",
        "guided_success",
    } and not _independent_demonstration(dimensions):
        proposals.append(("open_learning_loop", "Independent understanding or application of this concept remains unverified."))
    if dimensions.get("strategy_effectiveness") in {"helped", "enabled_independent_success"}:
        proposals.append(("recent_strategy_success", "A teaching strategy had an observable recent positive outcome."))
    if dimensions.get("strategy_effectiveness") == "ineffective":
        proposals.append(("recent_strategy_failure", "A teaching strategy did not improve the observed learning outcome."))
    if dimensions.get("retention") in {"retrieval_failed", "partial_retrieval"}:
        proposals.append(("current_retention_concern", "Recent validated evidence indicates this concept needs a retention revisit."))
    if event.event_type == "current_focus_signal":
        proposals.append(("current_school_focus", "Recent validated evidence identifies the current school learning focus."))
    if event.event_type == "support_change" and evidence.relationship == "improvement":
        proposals.append(("important_recent_change", "Recent validated evidence shows a meaningful change in support needs."))
    return proposals


def _independent_demonstration(dimensions: dict[str, object]) -> bool:
    return dimensions.get("understanding") in {"demonstrated", "strong_demonstration"} and dimensions.get(
        "independence"
    ) in {"independent", "light_support"}


def _partial_improvement(dimensions: dict[str, object], relationship: str) -> bool:
    return relationship == "improvement" and dimensions.get("understanding") == "partial"


def _upsert_active_state(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
    concept_ref: str | None,
    processing_run_id: UUID,
    state_type: str,
    detail: str,
    evidence_id: UUID,
    now: datetime,
    policy_version: str,
) -> CurrentLearningState:
    state = _matching_states(
        session,
        student_id=student_id,
        subject=subject,
        concept_ref=concept_ref,
        state_types=(state_type,),
        statuses=("ACTIVE", "RESOLVING"),
        policy_version=policy_version,
    ).first()
    if state is None:
        state = CurrentLearningState(
            student_id=student_id,
            processing_run_id=processing_run_id,
            subject=subject,
            state_type=state_type,
            concept_ref=concept_ref,
            detail=detail,
            status="ACTIVE",
            evidence_refs=[str(evidence_id)],
            policy_version=policy_version,
            detected_at=now,
            updated_at=now,
            expires_at=(now + _SHORT_LIVED_STATE_WINDOWS[state_type])
            if state_type in _SHORT_LIVED_STATE_WINDOWS
            else None,
        )
        session.add(state)
        session.flush()
        return state
    _append_evidence_ref(state, evidence_id=evidence_id)
    state.processing_run_id = processing_run_id
    state.detail = detail
    state.status = "ACTIVE"
    state.updated_at = now
    state.resolved_at = None
    if state_type in _SHORT_LIVED_STATE_WINDOWS:
        state.expires_at = now + _SHORT_LIVED_STATE_WINDOWS[state_type]
    return state


def _resolve_states(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
    concept_ref: str | None,
    state_types: tuple[str, ...],
    evidence_id: UUID,
    now: datetime,
    policy_version: str,
) -> list[CurrentLearningState]:
    states = list(
        _matching_states(
            session,
            student_id=student_id,
            subject=subject,
            concept_ref=concept_ref,
            state_types=state_types,
            statuses=("ACTIVE", "RESOLVING"),
            policy_version=policy_version,
        )
    )
    for state in states:
        _append_evidence_ref(state, evidence_id=evidence_id)
        state.status = "RESOLVED"
        state.resolved_at = now
        state.updated_at = now
    return states


def _mark_states_resolving(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
    concept_ref: str | None,
    state_types: tuple[str, ...],
    evidence_id: UUID,
    now: datetime,
    policy_version: str,
) -> list[CurrentLearningState]:
    states = list(
        _matching_states(
            session,
            student_id=student_id,
            subject=subject,
            concept_ref=concept_ref,
            state_types=state_types,
            statuses=("ACTIVE",),
            policy_version=policy_version,
        )
    )
    for state in states:
        _append_evidence_ref(state, evidence_id=evidence_id)
        state.status = "RESOLVING"
        state.updated_at = now
    return states


def _matching_states(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
    concept_ref: str | None,
    state_types: tuple[str, ...],
    statuses: tuple[str, ...],
    policy_version: str,
):
    query = select(CurrentLearningState).where(
        CurrentLearningState.student_id == student_id,
        CurrentLearningState.subject == subject,
        CurrentLearningState.state_type.in_(state_types),
        CurrentLearningState.status.in_(statuses),
        CurrentLearningState.policy_version == policy_version,
    )
    if concept_ref is None:
        query = query.where(CurrentLearningState.concept_ref.is_(None))
    else:
        query = query.where(CurrentLearningState.concept_ref == concept_ref)
    return session.execute(
        query.order_by(CurrentLearningState.detected_at.desc(), CurrentLearningState.id)
    ).scalars()


def _append_evidence_ref(state: CurrentLearningState, *, evidence_id: UUID) -> None:
    evidence_refs = list(state.evidence_refs)
    reference = str(evidence_id)
    if reference not in evidence_refs:
        evidence_refs.append(reference)
        state.evidence_refs = evidence_refs
