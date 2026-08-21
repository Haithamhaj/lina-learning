"""Versioned deterministic Decision Views derived from Evidence and intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from services.intelligence.current_state import CURRENT_STATE_POLICY_VERSION
from services.intelligence.patterns import PATTERN_POLICY_VERSION
from services.platform.db.models import (
    CandidateEvent,
    CurrentLearningState,
    DecisionView,
    IntelligenceProcessingRun,
    IntelligenceSessionAuthority,
    LearnerPattern,
    LearningEvidence,
    LearningEvent,
    LearningSession,
)


DECISION_VIEW_POLICY_VERSION = "decision-view-policy-v1"
_VIEW_TYPES = ("learning_status", "independence", "retention", "strategy_effectiveness")
_CURRENT_NEEDS_ATTENTION_STATES = {"active_difficulty", "active_misconception", "open_learning_loop"}


@dataclass(frozen=True)
class DecisionViewPolicy:
    """Centralized calibration defaults; categorical conclusions remain the output."""

    version: str = DECISION_VIEW_POLICY_VERSION
    strong_evidence_count: int = 3
    high_confidence_task_count: int = 3
    medium_confidence_evidence_count: int = 2
    high_confidence_recency_window: timedelta = timedelta(days=30)


@dataclass(frozen=True)
class _EvidenceItem:
    evidence: LearningEvidence
    event: LearningEvent
    candidate: CandidateEvent

    @property
    def task_ref(self) -> str:
        payload = self.candidate.payload if isinstance(self.candidate.payload, dict) else {}
        value = payload.get("task_ref")
        return value if isinstance(value, str) and value else self.evidence.source_ref


def derive_decision_views(
    session: Session,
    *,
    student_id: UUID,
    processing_run_id: UUID,
    subject: str,
    concept_ref: str,
    policy: DecisionViewPolicy | None = None,
    now: datetime | None = None,
) -> list[DecisionView]:
    """Idempotently persist compact categorical views for one subject/concept.

    Evidence is always the primary input.  Current State and Pattern rows only
    supply current/historical context and are stored as provenance, never as
    independent learner facts.
    """

    effective_policy = policy or DecisionViewPolicy()
    effective_now = now or datetime.now(UTC)
    evidence = _evidence_items(session, student_id=student_id, subject=subject, concept_ref=concept_ref)
    states = _active_states(
        session,
        student_id=student_id,
        subject=subject,
        concept_ref=concept_ref,
        now=effective_now,
    )
    patterns = _current_patterns(session, student_id=student_id, subject=subject, concept_ref=concept_ref)
    result: list[DecisionView] = []
    for view_type in _VIEW_TYPES:
        conclusion, reason_evidence = _conclusion(view_type, evidence=evidence, states=states, policy=effective_policy)
        confidence = _confidence(reason_evidence, patterns=patterns, policy=effective_policy, now=effective_now)
        view = _upsert_view(
            session,
            student_id=student_id,
            processing_run_id=processing_run_id,
            subject=subject,
            concept_ref=concept_ref,
            view_type=view_type,
            conclusion=conclusion,
            confidence=confidence,
            explanation=_explanation(view_type, conclusion, reason_evidence),
            evidence_ids=[str(item.evidence.id) for item in evidence],
            state_ids=[str(state.id) for state in states],
            pattern_ids=[str(pattern.id) for pattern in patterns],
            source_versions={
                "decision_policy_version": effective_policy.version,
                "evidence_processing_run_ids": sorted({str(item.event.processing_run_id) for item in evidence}),
                "current_state_policy_version": CURRENT_STATE_POLICY_VERSION,
                "pattern_policy_version": PATTERN_POLICY_VERSION,
            },
            policy=effective_policy,
            now=effective_now,
        )
        result.append(view)
    session.flush()
    return result


def apply_processing_run_decision_views(
    session: Session,
    *,
    processing_run_id: UUID,
    policy: DecisionViewPolicy | None = None,
    now: datetime | None = None,
) -> list[DecisionView]:
    """Derive views for each subject/concept completed in one Evidence run."""

    run = session.get(IntelligenceProcessingRun, processing_run_id)
    if run is None:
        raise LookupError(f"Processing run {processing_run_id!r} does not exist.")
    scopes = session.execute(
        select(LearningEvent.subject, LearningEvidence.concept_ref)
        .join(LearningEvidence, LearningEvidence.event_id == LearningEvent.id)
        .where(
            LearningEvent.processing_run_id == processing_run_id,
            LearningEvidence.concept_ref.is_not(None),
        )
        .distinct()
        .order_by(LearningEvent.subject, LearningEvidence.concept_ref)
    ).all()
    result: list[DecisionView] = []
    for subject, concept_ref in scopes:
        if concept_ref is None:
            continue
        result.extend(
            derive_decision_views(
                session,
                student_id=run.student_id,
                processing_run_id=processing_run_id,
                subject=subject,
                concept_ref=concept_ref,
                policy=policy,
                now=now,
            )
        )
    return result


def _evidence_items(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
    concept_ref: str,
) -> list[_EvidenceItem]:
    rows = session.execute(
        select(LearningEvidence, LearningEvent, CandidateEvent, IntelligenceProcessingRun)
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .join(CandidateEvent, LearningEvent.candidate_event_id == CandidateEvent.id)
        .join(IntelligenceProcessingRun, LearningEvent.processing_run_id == IntelligenceProcessingRun.id)
        .where(
            IntelligenceProcessingRun.status == "COMPLETED",
            CandidateEvent.session_id.in_(select(LearningSession.id).where(LearningSession.student_id == student_id)),
        )
    ).all()
    authoritative_runs = {
        row.session_id: row.evidence_processing_run_id
        for row in session.execute(
            select(IntelligenceSessionAuthority).where(IntelligenceSessionAuthority.student_id == student_id)
        ).scalars()
    }
    selected: dict[UUID, tuple[_EvidenceItem, IntelligenceProcessingRun]] = {}
    for evidence, event, candidate, run in rows:
        authoritative_run_id = authoritative_runs.get(event.session_id)
        if authoritative_run_id is not None and event.processing_run_id != authoritative_run_id:
            continue
        item = _EvidenceItem(evidence, event, candidate)
        prior = selected.get(candidate.id)
        if prior is None or _version_key(run, event) > _version_key(prior[1], prior[0].event):
            selected[candidate.id] = (item, run)
    authoritative = (
        item
        for item, _ in selected.values()
        if item.event.subject == subject
        and item.event.concept_ref == concept_ref
        and item.evidence.concept_ref == concept_ref
    )
    return sorted(
        authoritative,
        key=lambda item: (item.candidate.created_at, str(item.candidate.id)),
    )


def _version_key(run: IntelligenceProcessingRun, event: LearningEvent) -> tuple[datetime, str, str]:
    """Latest completed interpretation wins for one immutable raw observation."""

    return run.created_at, str(run.id), str(event.id)


def _active_states(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
    concept_ref: str,
    now: datetime,
) -> list[CurrentLearningState]:
    return list(
        session.execute(
            select(CurrentLearningState).where(
                CurrentLearningState.student_id == student_id,
                CurrentLearningState.subject == subject,
                CurrentLearningState.concept_ref == concept_ref,
                CurrentLearningState.policy_version == CURRENT_STATE_POLICY_VERSION,
                CurrentLearningState.status == "ACTIVE",
                or_(CurrentLearningState.expires_at.is_(None), CurrentLearningState.expires_at > now),
            )
            .order_by(CurrentLearningState.updated_at.desc(), CurrentLearningState.id)
        ).scalars()
    )


def _current_patterns(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
    concept_ref: str,
) -> list[LearnerPattern]:
    return list(
        session.execute(
            select(LearnerPattern).where(
                LearnerPattern.student_id == student_id,
                LearnerPattern.policy_version == PATTERN_POLICY_VERSION,
                LearnerPattern.status.in_(("ACTIVE", "STABLE")),
                LearnerPattern.scope["subject"].astext == subject,
                LearnerPattern.scope["concept_ref"].astext == concept_ref,
            )
            .order_by(LearnerPattern.last_supported_at.desc(), LearnerPattern.id)
        ).scalars()
    )


def _conclusion(
    view_type: str,
    *,
    evidence: list[_EvidenceItem],
    states: list[CurrentLearningState],
    policy: DecisionViewPolicy,
) -> tuple[str, list[_EvidenceItem]]:
    if view_type == "learning_status":
        return _learning_status(evidence=evidence, states=states, policy=policy)
    if view_type == "independence":
        return _independence(evidence=evidence, states=states)
    if view_type == "retention":
        return _retention(evidence=evidence, states=states, policy=policy)
    return _strategy_effectiveness(evidence=evidence, policy=policy)


def _learning_status(
    *,
    evidence: list[_EvidenceItem],
    states: list[CurrentLearningState],
    policy: DecisionViewPolicy,
) -> tuple[str, list[_EvidenceItem]]:
    if any(state.state_type in _CURRENT_NEEDS_ATTENTION_STATES for state in states):
        return "NEEDS_ATTENTION", evidence
    if not evidence:
        return "INSUFFICIENT_EVIDENCE", []
    demonstrated = [
        item
        for item in evidence
        if item.evidence.dimensions.get("understanding") in {"demonstrated", "strong_demonstration"}
    ]
    partial = [item for item in evidence if item.evidence.dimensions.get("understanding") == "partial"]
    if (
        len(demonstrated) >= policy.strong_evidence_count
        and len({item.task_ref for item in demonstrated}) >= policy.high_confidence_task_count
    ):
        return "STRONG", demonstrated
    if demonstrated or partial:
        return "DEVELOPING", demonstrated or partial
    if any(item.evidence.dimensions.get("understanding") == "not_demonstrated" for item in evidence):
        return "NEEDS_ATTENTION", evidence
    return "INSUFFICIENT_EVIDENCE", []


def _independence(*, evidence: list[_EvidenceItem], states: list[CurrentLearningState]) -> tuple[str, list[_EvidenceItem]]:
    if any(state.state_type in _CURRENT_NEEDS_ATTENTION_STATES for state in states):
        return "NEEDS_ATTENTION", evidence
    observed = [item for item in evidence if item.evidence.dimensions.get("independence") != "not_applicable"]
    if not observed:
        return "INSUFFICIENT_EVIDENCE", []
    latest = observed[-1]
    level = latest.evidence.dimensions.get("independence")
    if level == "independent":
        return "STRONG", [latest]
    if level in {"light_support", "moderate_support"}:
        return "DEVELOPING", [latest]
    return "NEEDS_ATTENTION", [latest]


def _retention(
    *,
    evidence: list[_EvidenceItem],
    states: list[CurrentLearningState],
    policy: DecisionViewPolicy,
) -> tuple[str, list[_EvidenceItem]]:
    tested = [item for item in evidence if item.evidence.dimensions.get("retention") != "not_tested"]
    if any(state.state_type == "current_retention_concern" for state in states):
        return "NEEDS_ATTENTION", tested
    if not tested:
        return "INSUFFICIENT_EVIDENCE", []
    latest = tested[-1]
    retention = latest.evidence.dimensions.get("retention")
    if retention in {"retrieval_failed", "partial_retrieval"}:
        return "NEEDS_ATTENTION", tested
    retained = [item for item in tested if item.evidence.dimensions.get("retention") == "retained"]
    if (
        len(retained) >= policy.strong_evidence_count
        and len({item.task_ref for item in retained}) >= policy.high_confidence_task_count
    ):
        return "STRONG", retained
    return "DEVELOPING", tested


def _strategy_effectiveness(
    *,
    evidence: list[_EvidenceItem],
    policy: DecisionViewPolicy,
) -> tuple[str, list[_EvidenceItem]]:
    outcomes = [
        item
        for item in evidence
        if item.event.event_type == "strategy_outcome"
        and isinstance(
            (item.candidate.payload if isinstance(item.candidate.payload, dict) else {}).get("observed_student_outcome"),
            str,
        )
        and item.evidence.dimensions.get("strategy_effectiveness") in {"helped", "enabled_independent_success", "ineffective"}
    ]
    if not outcomes:
        return "INSUFFICIENT_EVIDENCE", []
    positive = [
        item
        for item in outcomes
        if item.evidence.dimensions.get("strategy_effectiveness") in {"helped", "enabled_independent_success"}
    ]
    negative = [item for item in outcomes if item.evidence.dimensions.get("strategy_effectiveness") == "ineffective"]
    if positive and negative:
        return "DEVELOPING", outcomes
    if (
        len(positive) >= policy.strong_evidence_count
        and len({item.task_ref for item in positive}) >= policy.high_confidence_task_count
    ):
        return "STRONG", positive
    if positive:
        return "DEVELOPING", positive
    return "NEEDS_ATTENTION", negative


def _confidence(
    evidence: list[_EvidenceItem],
    *,
    patterns: list[LearnerPattern],
    policy: DecisionViewPolicy,
    now: datetime,
) -> str:
    if not evidence:
        return "LOW"
    task_count = len({item.task_ref for item in evidence})
    polarity = {_polarity(item) for item in evidence}
    if len(polarity - {"neutral"}) > 1:
        return "LOW"
    latest_observed = max(item.candidate.created_at for item in evidence)
    if (
        len(evidence) >= policy.strong_evidence_count
        and task_count >= policy.high_confidence_task_count
        and latest_observed >= now - policy.high_confidence_recency_window
    ):
        return "HIGH"
    if len(evidence) >= policy.medium_confidence_evidence_count or patterns:
        return "MEDIUM"
    return "LOW"


def _polarity(item: _EvidenceItem) -> str:
    dimensions = item.evidence.dimensions
    if (
        dimensions.get("strategy_effectiveness") in {"helped", "enabled_independent_success"}
        or dimensions.get("understanding") in {"demonstrated", "strong_demonstration"}
        or dimensions.get("retention") in {"retained", "rapid_recovery"}
    ):
        return "positive"
    if (
        dimensions.get("strategy_effectiveness") == "ineffective"
        or dimensions.get("understanding") == "not_demonstrated"
        or dimensions.get("retention") in {"retrieval_failed", "partial_retrieval"}
    ):
        return "negative"
    return "neutral"


def _explanation(view_type: str, conclusion: str, evidence: list[_EvidenceItem]) -> str:
    if conclusion == "INSUFFICIENT_EVIDENCE":
        return f"Insufficient evidence — no validated {view_type.replace('_', ' ')} evidence is available."
    if conclusion == "NEEDS_ATTENTION":
        return f"Needs attention — validated current evidence indicates this {view_type.replace('_', ' ')} needs support."
    if conclusion == "STRONG":
        return f"Strong — {len(evidence)} validated, diverse supporting observations are available."
    if view_type == "learning_status" and any(item.evidence.dimensions.get("independence") == "independent" for item in evidence):
        return "Developing — recent validated independent demonstration is present; more diverse confirmation is needed."
    return f"Developing — validated evidence supports progress, with further confirmation still needed."


def _upsert_view(
    session: Session,
    *,
    student_id: UUID,
    processing_run_id: UUID,
    subject: str,
    concept_ref: str,
    view_type: str,
    conclusion: str,
    confidence: str,
    explanation: str,
    evidence_ids: list[str],
    state_ids: list[str],
    pattern_ids: list[str],
    source_versions: dict[str, object],
    policy: DecisionViewPolicy,
    now: datetime,
) -> DecisionView:
    view = session.execute(
        select(DecisionView)
        .where(
            DecisionView.student_id == student_id,
            DecisionView.processing_run_id == processing_run_id,
            DecisionView.subject == subject,
            DecisionView.concept_ref == concept_ref,
            DecisionView.view_type == view_type,
            DecisionView.policy_version == policy.version,
        )
        .with_for_update()
    ).scalar_one_or_none()
    values = {
        "conclusion": conclusion,
        "confidence": confidence,
        "explanation": explanation,
        "evidence_ids": evidence_ids,
        "state_ids": state_ids,
        "pattern_ids": pattern_ids,
        "source_versions": source_versions,
        "generated_at": now,
        # Keep legacy fields synchronized until a later explicit removal migration.
        "mastery": conclusion,
        "evidence_confidence": confidence,
    }
    if view is None:
        view = DecisionView(
            student_id=student_id,
            processing_run_id=processing_run_id,
            subject=subject,
            concept_ref=concept_ref,
            view_type=view_type,
            policy_version=policy.version,
            **values,
        )
        session.add(view)
    else:
        for field, value in values.items():
            setattr(view, field, value)
    session.flush()
    return view
