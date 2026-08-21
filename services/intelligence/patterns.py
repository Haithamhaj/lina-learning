"""Versioned deterministic Pattern lifecycle derived from TASK-021 Evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.intelligence.consolidation import SESSION_EVIDENCE_SCHEMA_VERSION
from services.platform.db.models import (
    CandidateEvent,
    IntelligenceProcessingRun,
    LearnerPattern,
    LearningEvidence,
    LearningEvent,
    LearningSession,
    PatternEvidence,
)


PATTERN_POLICY_VERSION = "pattern-policy-v1"


@dataclass(frozen=True)
class PatternPolicy:
    """Calibration defaults, deliberately centralized and versioned."""

    version: str = PATTERN_POLICY_VERSION
    active_support_count: int = 2
    stable_support_count: int = 3
    stable_unique_tasks: int = 3
    stable_min_span: timedelta = timedelta(days=7)
    recency_half_life: timedelta = timedelta(days=21)
    weakening_counter_score: float = 1.5
    resolution_counter_count: int = 2
    resolution_score_multiplier: float = 1.25
    scope_concept_count: int = 3
    scope_context_count: int = 2


PatternRole = Literal["supports", "contradicts", "improvement", "retention_failure"]


class PatternSourceError(ValueError):
    """The supplied row is not completed, validated TASK-021 Evidence."""


@dataclass(frozen=True)
class _EvidenceContext:
    evidence: LearningEvidence
    event: LearningEvent
    candidate: CandidateEvent
    learning_session: LearningSession
    run: IntelligenceProcessingRun
    observed_at: datetime
    task_ref: str
    context_ref: str


def apply_evidence_to_patterns(
    session: Session,
    *,
    evidence_id: UUID,
    now: datetime | None = None,
    policy: PatternPolicy | None = None,
) -> list[LearnerPattern]:
    """Derive or update only deterministic Pattern rows for one Evidence item.

    The operation is idempotent for a policy version and never creates a Card,
    Current State, or decision view.
    """

    effective_policy = _effective_policy(policy)
    item = _load_validated_evidence(session, evidence_id=evidence_id)
    targets = _pattern_targets(session, item=item, policy=effective_policy)
    if not targets:
        return []

    touched: list[LearnerPattern] = []
    for pattern_type, pattern_key, role in targets:
        scope = _concept_scope(item)
        pattern = _upsert_pattern(
            session,
            item=item,
            pattern_type=pattern_type,
            pattern_key=pattern_key,
            scope=scope,
            policy=effective_policy,
        )
        _link_evidence(session, pattern=pattern, item=item, role=role, policy=effective_policy)
        _recompute_pattern(session, pattern=pattern, now=now or datetime.now(UTC), policy=effective_policy)
        if pattern not in touched:
            touched.append(pattern)
        for broader in _broaden_supported_scope(
            session,
            item=item,
            pattern_type=pattern_type,
            pattern_key=pattern_key,
            policy=effective_policy,
            now=now or datetime.now(UTC),
        ):
            if broader not in touched:
                touched.append(broader)
    session.flush()
    return touched


def apply_processing_run_patterns(
    session: Session,
    *,
    processing_run_id: UUID,
    now: datetime | None = None,
    policy: PatternPolicy | None = None,
) -> list[LearnerPattern]:
    """Idempotently derive the selected policy version from a TASK-021 run."""

    evidence_ids = session.execute(
        select(LearningEvidence.id)
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .join(CandidateEvent, LearningEvent.candidate_event_id == CandidateEvent.id)
        .where(LearningEvent.processing_run_id == processing_run_id)
        .order_by(CandidateEvent.created_at, LearningEvidence.id)
    ).scalars()
    result: list[LearnerPattern] = []
    for evidence_id in evidence_ids:
        for pattern in apply_evidence_to_patterns(
            session,
            evidence_id=evidence_id,
            now=now,
            policy=policy,
        ):
            if pattern not in result:
                result.append(pattern)
    return result


def _effective_policy(policy: PatternPolicy | None) -> PatternPolicy:
    if policy is not None:
        return policy
    # This keeps a controlled version override useful for deterministic rebuilds.
    return PatternPolicy(version=PATTERN_POLICY_VERSION)


def _load_validated_evidence(session: Session, *, evidence_id: UUID) -> _EvidenceContext:
    row = session.execute(
        select(LearningEvidence, LearningEvent, CandidateEvent, LearningSession, IntelligenceProcessingRun)
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .join(CandidateEvent, LearningEvent.candidate_event_id == CandidateEvent.id)
        .join(LearningSession, LearningEvent.session_id == LearningSession.id)
        .join(IntelligenceProcessingRun, LearningEvent.processing_run_id == IntelligenceProcessingRun.id)
        .where(LearningEvidence.id == evidence_id)
    ).one_or_none()
    if row is None:
        raise PatternSourceError("Evidence does not exist.")
    evidence, event, candidate, learning_session, run = row
    run_scope = run.scope if isinstance(run.scope, dict) else {}
    if (
        run.status != "COMPLETED"
        or learning_session.status != "CLOSED"
        or run_scope.get("consolidation_schema_version") != SESSION_EVIDENCE_SCHEMA_VERSION
        or run_scope.get("session_id") != str(learning_session.id)
        or event.subject != "MATH"
        or evidence.concept_ref != event.concept_ref
    ):
        raise PatternSourceError("Patterns require completed, validated TASK-021 Math Evidence.")
    payload = candidate.payload if isinstance(candidate.payload, dict) else {}
    observed_at = candidate.created_at or learning_session.closed_at or datetime.now(UTC)
    return _EvidenceContext(
        evidence=evidence,
        event=event,
        candidate=candidate,
        learning_session=learning_session,
        run=run,
        observed_at=observed_at,
        task_ref=_normalized_token(payload.get("task_ref"), fallback=f"concept:{event.concept_ref or 'unknown'}"),
        context_ref=_normalized_token(payload.get("context_ref"), fallback="math_practice"),
    )


def _pattern_targets(
    session: Session,
    *,
    item: _EvidenceContext,
    policy: PatternPolicy,
) -> list[tuple[str, str, PatternRole]]:
    dimensions = item.evidence.dimensions
    supports_need = dimensions.get("understanding") in {"not_demonstrated", "partial"} or dimensions.get(
        "independence"
    ) in {"moderate_support", "substantial_support", "full_teaching"}
    independent = dimensions.get("understanding") in {"demonstrated", "strong_demonstration"} and dimensions.get(
        "independence"
    ) in {"independent", "light_support"}
    relationship = item.evidence.relationship
    targets: list[tuple[str, str, PatternRole]] = []
    if supports_need:
        targets.append(("support_need", "support_need", "supports"))
    elif independent and relationship in {"contradicts", "improvement"}:
        targets.append(("support_need", "support_need", relationship))

    if item.event.event_type == "misconception_signal":
        targets.append(("misconception_recurrence", f"misconception:{_normalized_token(item.candidate.signal, fallback='observed')}", "supports"))
    elif independent and relationship in {"contradicts", "improvement"}:
        misconception_key = _matching_misconception_key(session, item=item, policy=policy)
        if misconception_key is not None:
            targets.append(("misconception_recurrence", misconception_key, relationship))

    strategy_key = _normalized_token((item.candidate.payload or {}).get("strategy_key"), fallback="")
    strategy_outcome = (item.candidate.payload or {}).get("observed_student_outcome")
    if item.event.event_type == "strategy_outcome" and strategy_key and isinstance(strategy_outcome, str):
        effectiveness = dimensions.get("strategy_effectiveness")
        if effectiveness in {"helped", "enabled_independent_success"}:
            targets.append(("strategy_effectiveness", f"strategy:{strategy_key}", "supports"))
        elif effectiveness == "ineffective":
            targets.append(("strategy_effectiveness", f"strategy:{strategy_key}", "contradicts"))

    if item.event.event_type == "support_change" and dimensions.get("independence") in {"independent", "light_support"}:
        targets.append(("independence_support_change", "independence_gain", "supports"))
    if dimensions.get("retention") in {"retrieval_failed", "partial_retrieval"}:
        targets.append(("retention_tendency", "retention_support_need", "supports"))
    if dimensions.get("retention") in {"retained", "rapid_recovery"} and relationship in {"contradicts", "improvement"}:
        targets.append(("retention_tendency", "retention_support_need", relationship))
    persistence = dimensions.get("persistence")
    if persistence in {"continued_independently", "continued_with_support", "stopped"}:
        targets.append(("learning_behavior", f"persistence:{persistence}", "supports"))
    return targets


def _matching_misconception_key(
    session: Session,
    *,
    item: _EvidenceContext,
    policy: PatternPolicy,
) -> str | None:
    normalized_signal = _normalized_token(item.candidate.signal, fallback="")
    if not normalized_signal:
        return None
    pattern_key = f"misconception:{normalized_signal}"
    existing = session.execute(
        select(LearnerPattern.id).where(
            LearnerPattern.student_id == item.learning_session.student_id,
            LearnerPattern.policy_version == policy.version,
            LearnerPattern.pattern_type == "misconception_recurrence",
            LearnerPattern.pattern_key == pattern_key,
            LearnerPattern.scope_key == _scope_key(_concept_scope(item)),
        )
    ).scalar_one_or_none()
    return pattern_key if existing is not None else None


def _concept_scope(item: _EvidenceContext) -> dict[str, str]:
    return {
        "scope_type": "concept",
        "subject": item.event.subject,
        "concept_ref": item.event.concept_ref or "unknown",
    }


def _upsert_pattern(
    session: Session,
    *,
    item: _EvidenceContext,
    pattern_type: str,
    pattern_key: str,
    scope: dict[str, str],
    policy: PatternPolicy,
) -> LearnerPattern:
    scope_key = _scope_key(scope)
    pattern = session.execute(
        select(LearnerPattern)
        .where(
            LearnerPattern.student_id == item.learning_session.student_id,
            LearnerPattern.policy_version == policy.version,
            LearnerPattern.pattern_type == pattern_type,
            LearnerPattern.pattern_key == pattern_key,
            LearnerPattern.scope_key == scope_key,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if pattern is None:
        pattern = LearnerPattern(
            student_id=item.learning_session.student_id,
            processing_run_id=item.run.id,
            pattern_type=pattern_type,
            pattern_key=pattern_key,
            scope=scope,
            scope_key=scope_key,
            policy_version=policy.version,
            status="CANDIDATE",
            support_count=0,
            counter_count=0,
            detail=_detail(pattern_type, scope),
            first_detected_at=item.observed_at,
            cycle_started_at=item.observed_at,
            cycle_number=1,
        )
        session.add(pattern)
        session.flush()
    elif pattern.status == "RESOLVED":
        # Keep all old links, but score a fresh recurrence lifecycle separately.
        pattern.status = "CANDIDATE"
        pattern.cycle_started_at = item.observed_at
        pattern.cycle_number += 1
        pattern.support_count = 0
        pattern.counter_count = 0
    pattern.processing_run_id = item.run.id
    return pattern


def _link_evidence(
    session: Session,
    *,
    pattern: LearnerPattern,
    item: _EvidenceContext,
    role: PatternRole,
    policy: PatternPolicy,
) -> None:
    exists = session.execute(
        select(PatternEvidence.id).where(
            PatternEvidence.pattern_id == pattern.id,
            PatternEvidence.evidence_id == item.evidence.id,
        )
    ).scalar_one_or_none()
    if exists is None:
        session.add(
            PatternEvidence(
                pattern_id=pattern.id,
                evidence_id=item.evidence.id,
                relationship=role,
                processing_run_id=item.run.id,
                policy_version=policy.version,
                task_ref=item.task_ref,
                context_ref=item.context_ref,
                cycle_number=pattern.cycle_number,
                observed_at=item.observed_at,
            )
        )
        session.flush()


def _recompute_pattern(session: Session, *, pattern: LearnerPattern, now: datetime, policy: PatternPolicy) -> None:
    rows = _cycle_links(session, pattern=pattern)
    support_links = [row for row in rows if row[0].relationship in {"supports", "retention_failure"}]
    counter_links = [row for row in rows if row[0].relationship in {"contradicts", "improvement"}]
    support_score = sum(_weighted_score(link, evidence, now=now, policy=policy, is_counter=False) for link, evidence in support_links)
    counter_score = sum(_weighted_score(link, evidence, now=now, policy=policy, is_counter=True) for link, evidence in counter_links)
    pattern.support_count = len(support_links)
    pattern.counter_count = len(counter_links)
    if support_links:
        pattern.last_supported_at = max(link.observed_at for link, _ in support_links)
    if counter_links:
        pattern.last_challenged_at = max(link.observed_at for link, _ in counter_links)

    if (
        len(counter_links) >= policy.resolution_counter_count
        and counter_score >= max(policy.weakening_counter_score, support_score * policy.resolution_score_multiplier)
    ):
        pattern.status = "RESOLVED"
        pattern.resolved_at = now
    elif counter_score >= policy.weakening_counter_score and (
        counter_score >= support_score or pattern.pattern_type == "strategy_effectiveness"
    ):
        pattern.status = "WEAKENING"
    elif len(support_links) >= policy.stable_support_count and _is_stable(support_links, policy=policy):
        pattern.status = "STABLE"
    elif len(support_links) >= policy.active_support_count:
        pattern.status = "ACTIVE"
    else:
        pattern.status = "CANDIDATE"


def _cycle_links(session: Session, *, pattern: LearnerPattern) -> list[tuple[PatternEvidence, LearningEvidence]]:
    rows = session.execute(
        select(PatternEvidence, LearningEvidence)
        .join(LearningEvidence, PatternEvidence.evidence_id == LearningEvidence.id)
        .where(
            PatternEvidence.pattern_id == pattern.id,
            PatternEvidence.policy_version == pattern.policy_version,
            PatternEvidence.cycle_number == pattern.cycle_number,
        )
    ).all()
    return list(rows)


def _weighted_score(
    link: PatternEvidence,
    evidence: LearningEvidence,
    *,
    now: datetime,
    policy: PatternPolicy,
    is_counter: bool,
) -> float:
    elapsed = max((now - link.observed_at).total_seconds(), 0.0)
    decay = 0.5 ** (elapsed / policy.recency_half_life.total_seconds())
    dimensions = evidence.dimensions
    quality = 1.0
    if dimensions.get("independence") == "independent":
        quality += 1.0
    if dimensions.get("understanding") == "strong_demonstration":
        quality += 0.75
    if dimensions.get("transfer") == "demonstrated":
        quality += 0.5
    if is_counter and link.relationship == "improvement":
        quality += 0.75
    if is_counter and evidence.dimensions.get("strategy_effectiveness") == "ineffective":
        quality += 1.5
    return quality * decay


def _is_stable(support_links: list[tuple[PatternEvidence, LearningEvidence]], *, policy: PatternPolicy) -> bool:
    observed = [link.observed_at for link, _ in support_links]
    if max(observed) - min(observed) < policy.stable_min_span:
        return False
    task_refs = {link.task_ref for link, _ in support_links}
    return len(task_refs) >= policy.stable_unique_tasks


def _broaden_supported_scope(
    session: Session,
    *,
    item: _EvidenceContext,
    pattern_type: str,
    pattern_key: str,
    policy: PatternPolicy,
    now: datetime,
) -> list[LearnerPattern]:
    source_rows = _matching_support_rows(
        session,
        student_id=item.learning_session.student_id,
        policy_version=policy.version,
        pattern_type=pattern_type,
        pattern_key=pattern_key,
    )
    current_source_rows = [
        row
        for row in source_rows
        if row[5].status not in {"RESOLVED", "SUPERSEDED", "WEAKENING"}
    ]
    grouped: dict[
        str,
        list[tuple[PatternEvidence, LearningEvidence, LearningEvent, CandidateEvent, IntelligenceProcessingRun, LearnerPattern]],
    ] = {}
    for row in current_source_rows:
        link, evidence, event, candidate, run, source_pattern = row
        payload = candidate.payload if isinstance(candidate.payload, dict) else {}
        context_ref = _normalized_token(payload.get("context_ref"), fallback="math_practice")
        grouped.setdefault(context_ref, []).append(row)
    result: list[LearnerPattern] = []
    existing_context_patterns = _existing_scope_patterns(
        session,
        student_id=item.learning_session.student_id,
        policy_version=policy.version,
        pattern_type=pattern_type,
        pattern_key=pattern_key,
        scope_type="context",
    )
    existing_context_by_ref = {
        str(pattern.scope.get("context_ref")): pattern
        for pattern in existing_context_patterns
        if isinstance(pattern.scope, dict) and isinstance(pattern.scope.get("context_ref"), str)
    }
    for context_ref in set(grouped).union(existing_context_by_ref):
        rows = grouped.get(context_ref, [])
        qualifies = _distinct_concept_count(rows) >= policy.scope_concept_count
        broader = existing_context_by_ref.get(context_ref)
        if qualifies:
            scope = {"scope_type": "context", "subject": "MATH", "context_ref": context_ref}
            broader = _upsert_pattern(
                session,
                item=item,
                pattern_type=pattern_type,
                pattern_key=pattern_key,
                scope=scope,
                policy=policy,
            )
            for link, evidence, event, candidate, run, source_pattern in rows:
                source_item = _EvidenceContext(
                    evidence=evidence,
                    event=event,
                    candidate=candidate,
                    learning_session=item.learning_session,
                    run=run,
                    observed_at=link.observed_at,
                    task_ref=_normalized_token((candidate.payload or {}).get("task_ref"), fallback=evidence.source_ref),
                    context_ref=context_ref,
                )
                _link_evidence(session, pattern=broader, item=source_item, role="supports", policy=policy)
        if broader is not None:
            _recompute_scope_pattern(
                broader,
                rows=rows,
                qualifies=qualifies,
                now=now,
                policy=policy,
            )
            result.append(broader)

    qualifying_contexts = {
        context
        for context, rows in grouped.items()
        if _distinct_concept_count(rows) >= policy.scope_concept_count
    }
    subject_rows = [row for rows in grouped.values() for row in rows]
    subject_qualifies = len(qualifying_contexts) >= policy.scope_context_count
    existing_subject = _existing_scope_patterns(
        session,
        student_id=item.learning_session.student_id,
        policy_version=policy.version,
        pattern_type=pattern_type,
        pattern_key=pattern_key,
        scope_type="subject",
    )
    subject = existing_subject[0] if existing_subject else None
    if subject_qualifies:
        scope = {"scope_type": "subject", "subject": "MATH"}
        subject = _upsert_pattern(session, item=item, pattern_type=pattern_type, pattern_key=pattern_key, scope=scope, policy=policy)
        for link, evidence, event, candidate, run, source_pattern in subject_rows:
            source_item = _EvidenceContext(evidence, event, candidate, item.learning_session, run, link.observed_at, evidence.source_ref, "math_practice")
            _link_evidence(session, pattern=subject, item=source_item, role="supports", policy=policy)
    if subject is not None:
        _recompute_scope_pattern(
            subject,
            rows=subject_rows,
            qualifies=subject_qualifies,
            now=now,
            policy=policy,
        )
        result.append(subject)
    # Math is the only source accepted by this implementation.  Deliberately no
    # cross-subject or global promotion exists until evidence can support it.
    return result


def _matching_support_rows(
    session: Session,
    *,
    student_id: UUID,
    policy_version: str,
    pattern_type: str,
    pattern_key: str,
) -> list[tuple[PatternEvidence, LearningEvidence, LearningEvent, CandidateEvent, IntelligenceProcessingRun, LearnerPattern]]:
    return list(
        session.execute(
            select(PatternEvidence, LearningEvidence, LearningEvent, CandidateEvent, IntelligenceProcessingRun, LearnerPattern)
            .join(LearnerPattern, PatternEvidence.pattern_id == LearnerPattern.id)
            .join(LearningEvidence, PatternEvidence.evidence_id == LearningEvidence.id)
            .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
            .join(CandidateEvent, LearningEvent.candidate_event_id == CandidateEvent.id)
            .join(IntelligenceProcessingRun, LearningEvent.processing_run_id == IntelligenceProcessingRun.id)
            .where(
                LearnerPattern.student_id == student_id,
                LearnerPattern.policy_version == policy_version,
                LearnerPattern.pattern_type == pattern_type,
                LearnerPattern.pattern_key == pattern_key,
                LearnerPattern.scope["scope_type"].astext == "concept",
                PatternEvidence.relationship == "supports",
                PatternEvidence.cycle_number == LearnerPattern.cycle_number,
            )
        ).all()
    )


def _existing_scope_patterns(
    session: Session,
    *,
    student_id: UUID,
    policy_version: str,
    pattern_type: str,
    pattern_key: str,
    scope_type: str,
) -> list[LearnerPattern]:
    return list(
        session.execute(
            select(LearnerPattern).where(
                LearnerPattern.student_id == student_id,
                LearnerPattern.policy_version == policy_version,
                LearnerPattern.pattern_type == pattern_type,
                LearnerPattern.pattern_key == pattern_key,
                LearnerPattern.scope["scope_type"].astext == scope_type,
            )
        ).scalars()
    )


def _distinct_concept_count(
    rows: list[tuple[PatternEvidence, LearningEvidence, LearningEvent, CandidateEvent, IntelligenceProcessingRun, LearnerPattern]],
) -> int:
    return len({event.concept_ref for _, _, event, _, _, _ in rows if event.concept_ref})


def _recompute_scope_pattern(
    pattern: LearnerPattern,
    *,
    rows: list[tuple[PatternEvidence, LearningEvidence, LearningEvent, CandidateEvent, IntelligenceProcessingRun, LearnerPattern]],
    qualifies: bool,
    now: datetime,
    policy: PatternPolicy,
) -> None:
    support_links = [(link, evidence) for link, evidence, _, _, _, _ in rows]
    pattern.support_count = len(support_links)
    if support_links:
        pattern.last_supported_at = max(link.observed_at for link, _ in support_links)
    if not qualifies:
        if pattern.status == "RESOLVED":
            return
        if support_links:
            pattern.status = "WEAKENING"
        else:
            pattern.status = "RESOLVED"
            pattern.resolved_at = now
        return
    if len(support_links) >= policy.stable_support_count and _is_stable(support_links, policy=policy):
        pattern.status = "STABLE"
    elif len(support_links) >= policy.active_support_count:
        pattern.status = "ACTIVE"
    else:
        pattern.status = "CANDIDATE"


def _scope_key(scope: dict[str, str]) -> str:
    return json.dumps(scope, sort_keys=True, separators=(",", ":"))


def _normalized_token(value: object, *, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    normalized = "".join(character if character.isalnum() else "_" for character in value.casefold()).strip("_")
    return normalized[:120] or fallback


def _detail(pattern_type: str, scope: dict[str, str]) -> str:
    scope_label = scope.get("concept_ref") or scope.get("context_ref") or scope.get("subject", "MATH")
    labels = {
        "support_need": "Repeated validated evidence indicates support may be useful",
        "misconception_recurrence": "A misconception signal has recurred",
        "strategy_effectiveness": "A strategy has validated observable outcomes",
        "independence_support_change": "Independence has changed across validated evidence",
        "retention_tendency": "A retention tendency has recurred",
        "learning_behavior": "A learning behavior has recurred",
    }
    return f"{labels[pattern_type]} in {scope_label}."
