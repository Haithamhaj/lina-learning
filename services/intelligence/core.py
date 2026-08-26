"""Deterministic Phase 3 intelligence derivation from preserved raw history."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import (
    CandidateEvent, CurrentLearningState, IntelligenceProcessingRun,
    LearnerIntelligenceCard, LearnerPattern, LearningEvent, LearningEvidence,
    LearningSession, PatternEvidence,
)
from services.intelligence.selection import select_relevant_intelligence_text
from services.tutor.exchanges import clear_session_exchange_embeddings

RUBRIC_VERSION = "evidence-rubric-v1"
PATTERN_POLICY_VERSION = "pattern-policy-v1"


def consolidate_student_history(
    session: Session,
    *,
    student_id: UUID,
    session_ids: list[UUID] | None = None,
) -> IntelligenceProcessingRun:
    """Create a new, auditable derived version from raw candidate history."""

    scope: dict[str, object] = {"session_ids": [str(value) for value in session_ids] if session_ids else "all"}
    run = IntelligenceProcessingRun(student_id=student_id, rubric_version=RUBRIC_VERSION, policy_version=PATTERN_POLICY_VERSION, scope=scope)
    session.add(run); session.flush()
    query = select(CandidateEvent, LearningSession).join(LearningSession, CandidateEvent.session_id == LearningSession.id).where(LearningSession.student_id == student_id)
    if session_ids:
        query = query.where(CandidateEvent.session_id.in_(session_ids))
    candidates = session.execute(query.order_by(CandidateEvent.created_at)).all()
    evidence_by_concept: dict[str, list[LearningEvidence]] = defaultdict(list)
    for candidate, learning_session in candidates:
        event = LearningEvent(
            processing_run_id=run.id, session_id=candidate.session_id, candidate_event_id=candidate.id,
            subject=learning_session.subject, concept_ref=candidate.concept_ref,
            event_type=candidate.event_type, description=f"{candidate.event_type}: {candidate.signal}",
            source_message_id=candidate.message_id,
        )
        session.add(event); session.flush()
        dimensions, relationship = _evidence_for(candidate.signal)
        evidence = LearningEvidence(
            event_id=event.id, concept_ref=candidate.concept_ref, dimensions=dimensions,
            relationship=relationship, source_ref=f"session:{candidate.session_id}:candidate:{candidate.id}",
        )
        session.add(evidence); session.flush()
        if candidate.concept_ref:
            evidence_by_concept[candidate.concept_ref].append(evidence)
    patterns: list[LearnerPattern] = []
    states: list[CurrentLearningState] = []
    for concept, evidence_items in evidence_by_concept.items():
        needs_support = [item for item in evidence_items if item.dimensions.get("understanding") in {"partial", "not_demonstrated"}]
        successes = [item for item in evidence_items if item.dimensions.get("understanding") in {"demonstrated", "strong_demonstration"}]
        if needs_support:
            states.append(CurrentLearningState(student_id=student_id, processing_run_id=run.id, state_type="active_difficulty", concept_ref=concept, detail=f"Recent evidence shows a current need for support with {concept}.", evidence_refs=[str(item.id) for item in needs_support[-2:]]))
        support_count, counter_count = len(needs_support), len(successes)
        status = _pattern_status(support_count, counter_count)
        pattern = LearnerPattern(student_id=student_id, processing_run_id=run.id, pattern_type="support_need", pattern_key=f"support_need:{concept}", scope={"subject": "MATH", "concept_ref": concept}, status=status, support_count=support_count, counter_count=counter_count, detail=f"Support need for {concept} derived from {support_count} support signals and {counter_count} independent/strong signals.")
        session.add(pattern); session.flush(); patterns.append(pattern)
        for evidence in evidence_items:
            session.add(PatternEvidence(pattern_id=pattern.id, evidence_id=evidence.id))
    for state in states:
        session.add(state)
    session.flush()
    card = _materialize_card(student_id, run, states, patterns)
    session.add(card); session.flush()
    return run


def close_and_consolidate(session: Session, *, learning_session: LearningSession) -> IntelligenceProcessingRun:
    """Development-close path mirrors the worker-owned session lifecycle."""

    learning_session.status = "CLOSED"
    clear_session_exchange_embeddings(session, learning_session=learning_session)
    return consolidate_student_history(session, student_id=learning_session.student_id)


def select_relevant_intelligence(session: Session, *, student_id: UUID, subject: str, question: str, budget: int = 900) -> list[str]:
    """Compatibility text view over the question-relevant selector."""

    return select_relevant_intelligence_text(
        session=session,
        student_id=student_id,
        subject=subject,
        question=question,
        character_budget=budget,
    )


def _evidence_for(signal: str) -> tuple[dict[str, object], str]:
    if signal in {"needs_hint", "incorrect_attempt"}:
        return ({"understanding": "partial", "independence": "light_support", "reasoning_demonstration": "not_observed", "retention": "not_tested"}, "supports")
    return ({"understanding": "demonstrated", "independence": "independent", "reasoning_demonstration": "coherent", "retention": "not_tested"}, "improvement")


def _pattern_status(support_count: int, counter_count: int) -> str:
    if counter_count >= support_count and counter_count > 0:
        return "RESOLVED"
    if support_count >= 3:
        return "STABLE"
    if support_count >= 2:
        return "ACTIVE"
    return "CANDIDATE"


def _materialize_card(student_id: UUID, run: IntelligenceProcessingRun, states: list[CurrentLearningState], patterns: list[LearnerPattern]) -> LearnerIntelligenceCard:
    entries = [f"MATH current state: {state.detail}" for state in states if state.status == "ACTIVE"]
    entries.extend(f"MATH pattern ({pattern.status}): {pattern.detail}" for pattern in patterns if pattern.status not in {"RESOLVED", "SUPERSEDED"})
    compact = entries[:6]
    return LearnerIntelligenceCard(student_id=student_id, processing_run_id=run.id, payload={"version": run.policy_version, "entries": compact, "budget": 900})
