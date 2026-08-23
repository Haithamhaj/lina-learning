"""Deterministic contracts for evidence-driven Current Learning State."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import services.intelligence.current_state as current_state_module
from services.intelligence.current_state import (
    CURRENT_STATE_POLICY_VERSION,
    apply_evidence_to_current_state,
    expire_current_states,
)
from services.intelligence.selection import select_relevant_intelligence
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CandidateEvent,
    CurrentLearningState,
    DecisionView,
    IntelligenceProcessingRun,
    LearnerIntelligenceCard,
    LearnerPattern,
    LearningEvidence,
    LearningEvent,
    LearningSession,
    Student,
    User,
)


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Current Learning State tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE ai_executions, jobs, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _dimensions(**overrides: str) -> dict[str, str]:
    values = {
        "understanding": "not_observed",
        "independence": "not_applicable",
        "reasoning_demonstration": "not_observed",
        "transfer": "not_tested",
        "self_correction": "not_observed",
        "retention": "not_tested",
        "strategy_effectiveness": "not_evaluable",
        "persistence": "not_observed",
        "confidence_calibration": "not_observed",
    }
    values.update(overrides)
    return values


def _validated_evidence(
    session: Session,
    *,
    subject: str = "MATH",
    concept_ref: str = "equivalent_fractions",
    event_type: str = "learning_attempt",
    dimensions: dict[str, str] | None = None,
    relationship: str = "insufficient",
) -> tuple[LearningEvidence, Student]:
    user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id)
    session.add(student)
    session.flush()
    learning_session = LearningSession(student_id=student.id, subject=subject, status="CLOSED")
    session.add(learning_session)
    session.flush()
    run = IntelligenceProcessingRun(
        student_id=student.id,
        rubric_version="evidence-rubric-v1",
        policy_version="session-consolidation-policy-v1",
        status="COMPLETED",
        scope={
            "session_id": str(learning_session.id),
            "consolidation_schema_version": "session-evidence-v1",
            "prompt_version": "session-evidence-prompt-v1",
            "provider": "fixture",
            "model": "fixture-evidence",
        },
    )
    session.add(run)
    session.flush()
    candidate = CandidateEvent(
        session_id=learning_session.id,
        message_id=None,
        event_type=event_type,
        concept_ref=concept_ref,
        signal="fixture",
        payload={},
    )
    session.add(candidate)
    session.flush()
    event = LearningEvent(
        processing_run_id=run.id,
        session_id=learning_session.id,
        candidate_event_id=candidate.id,
        subject=subject,
        concept_ref=concept_ref,
        event_type=event_type,
        description="Validated source-grounded fixture event.",
        source_message_id=None,
    )
    session.add(event)
    session.flush()
    evidence = LearningEvidence(
        event_id=event.id,
        concept_ref=concept_ref,
        dimensions=dimensions or _dimensions(),
        relationship=relationship,
        source_ref=f"fixture:{event.id}",
    )
    session.add(evidence)
    session.flush()
    return evidence, student


def _next_validated_evidence(
    session: Session,
    *,
    student: Student,
    subject: str = "MATH",
    concept_ref: str = "equivalent_fractions",
    event_type: str = "independent_success",
    dimensions: dict[str, str],
    relationship: str = "improvement",
) -> LearningEvidence:
    learning_session = LearningSession(student_id=student.id, subject=subject, status="CLOSED")
    session.add(learning_session)
    session.flush()
    run = IntelligenceProcessingRun(
        student_id=student.id,
        rubric_version="evidence-rubric-v1",
        policy_version="session-consolidation-policy-v1",
        status="COMPLETED",
        scope={
            "session_id": str(learning_session.id),
            "consolidation_schema_version": "session-evidence-v1",
            "prompt_version": "session-evidence-prompt-v1",
            "provider": "fixture",
            "model": "fixture-evidence",
        },
    )
    session.add(run)
    session.flush()
    candidate = CandidateEvent(
        session_id=learning_session.id,
        message_id=None,
        event_type=event_type,
        concept_ref=concept_ref,
        signal="fixture",
        payload={},
    )
    session.add(candidate)
    session.flush()
    event = LearningEvent(
        processing_run_id=run.id,
        session_id=learning_session.id,
        candidate_event_id=candidate.id,
        subject=subject,
        concept_ref=concept_ref,
        event_type=event_type,
        description="Later validated source-grounded fixture event.",
        source_message_id=None,
    )
    session.add(event)
    session.flush()
    evidence = LearningEvidence(
        event_id=event.id,
        concept_ref=concept_ref,
        dimensions=dimensions,
        relationship=relationship,
        source_ref=f"fixture:{event.id}",
    )
    session.add(evidence)
    session.flush()
    return evidence


def test_strong_difficulty_evidence_creates_a_subject_scoped_active_difficulty(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        evidence, student = _validated_evidence(
            session,
            dimensions=_dimensions(understanding="not_demonstrated", independence="substantial_support"),
        )

        states = apply_evidence_to_current_state(session, evidence_id=evidence.id)

        assert len(states) == 2  # difficulty plus an unresolved learning loop
        difficulty = next(state for state in states if state.state_type == "active_difficulty")
        assert (difficulty.student_id, difficulty.subject, difficulty.concept_ref, difficulty.status) == (
            student.id,
            "MATH",
            "equivalent_fractions",
            "ACTIVE",
        )
        assert difficulty.policy_version == CURRENT_STATE_POLICY_VERSION
        assert str(evidence.id) in difficulty.evidence_refs


def test_misconception_evidence_creates_an_active_misconception(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        evidence, _ = _validated_evidence(
            session,
            event_type="misconception_signal",
            dimensions=_dimensions(understanding="not_demonstrated"),
        )

        states = apply_evidence_to_current_state(session, evidence_id=evidence.id)

        assert any(state.state_type == "active_misconception" for state in states)


def test_guided_or_full_teaching_never_creates_an_independent_success_state(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        evidence, _ = _validated_evidence(
            session,
            event_type="guided_success",
            dimensions=_dimensions(understanding="demonstrated", independence="full_teaching"),
        )

        states = apply_evidence_to_current_state(session, evidence_id=evidence.id)

        assert not any(state.state_type == "important_recent_change" for state in states)
        assert any(state.state_type == "open_learning_loop" for state in states)


def test_strategy_without_observable_effectiveness_creates_no_strategy_success_state(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        evidence, _ = _validated_evidence(
            session,
            event_type="strategy_outcome",
            dimensions=_dimensions(strategy_effectiveness="not_evaluable"),
        )

        states = apply_evidence_to_current_state(session, evidence_id=evidence.id)

        assert not any(state.state_type == "recent_strategy_success" for state in states)


def test_observable_strategy_outcome_creates_recent_strategy_success(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        evidence, _ = _validated_evidence(
            session,
            event_type="strategy_outcome",
            dimensions=_dimensions(strategy_effectiveness="enabled_independent_success"),
        )

        states = apply_evidence_to_current_state(session, evidence_id=evidence.id)

        strategy = next(state for state in states if state.state_type == "recent_strategy_success")
        assert strategy.expires_at is not None


def test_retention_failure_creates_current_retention_concern(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        evidence, _ = _validated_evidence(
            session,
            event_type="retention_check",
            dimensions=_dimensions(retention="retrieval_failed"),
        )

        states = apply_evidence_to_current_state(session, evidence_id=evidence.id)

        assert any(state.state_type == "current_retention_concern" for state in states)


def test_historical_current_focus_evidence_preserves_audit_rows_without_new_state(
    factory: sessionmaker[Session],
) -> None:
    """Fail if preserved historical focus data regains Current State authority."""

    with factory.begin() as session:
        evidence, _ = _validated_evidence(
            session,
            event_type="current_focus_signal",
        )

        states = apply_evidence_to_current_state(session, evidence_id=evidence.id)
        candidate = session.query(CandidateEvent).filter_by(
            event_type="current_focus_signal"
        ).one()

        assert states == []
        assert session.get(CandidateEvent, candidate.id) is candidate
        assert session.get(LearningEvent, evidence.event_id) is not None
        assert session.get(LearningEvidence, evidence.id) is evidence


@pytest.mark.parametrize(
    ("initial_type", "initial_event", "initial_dimensions", "resolution_event", "resolution_dimensions"),
    [
        (
            "active_difficulty",
            "incorrect_attempt",
            _dimensions(understanding="partial", independence="substantial_support"),
            "independent_success",
            _dimensions(understanding="demonstrated", independence="independent"),
        ),
        (
            "active_misconception",
            "misconception_signal",
            _dimensions(understanding="not_demonstrated"),
            "explanation_attempt",
            _dimensions(understanding="demonstrated", independence="light_support", reasoning_demonstration="coherent"),
        ),
        (
            "open_learning_loop",
            "open_loop_created",
            _dimensions(understanding="partial", independence="full_teaching"),
            "independent_success",
            _dimensions(understanding="demonstrated", independence="independent"),
        ),
        (
            "current_retention_concern",
            "retention_check",
            _dimensions(retention="partial_retrieval"),
            "retention_check",
            _dimensions(retention="retained", understanding="demonstrated", independence="independent"),
        ),
    ],
)
def test_newer_supported_evidence_resolves_the_matching_current_state(
    factory: sessionmaker[Session],
    initial_type: str,
    initial_event: str,
    initial_dimensions: dict[str, str],
    resolution_event: str,
    resolution_dimensions: dict[str, str],
) -> None:
    with factory.begin() as session:
        initial, student = _validated_evidence(
            session,
            event_type=initial_event,
            dimensions=initial_dimensions,
        )
        apply_evidence_to_current_state(session, evidence_id=initial.id)
        state = session.query(CurrentLearningState).filter_by(state_type=initial_type).one()
        later = _next_validated_evidence(
            session,
            student=student,
            event_type=resolution_event,
            dimensions=resolution_dimensions,
        )

        apply_evidence_to_current_state(session, evidence_id=later.id)

        assert state.status == "RESOLVED"
        assert state.resolved_at is not None
        assert str(later.id) in state.evidence_refs


def test_irrelevant_subject_evidence_cannot_change_math_current_state(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        evidence, student = _validated_evidence(
            session,
            dimensions=_dimensions(understanding="not_demonstrated", independence="substantial_support"),
        )
        apply_evidence_to_current_state(session, evidence_id=evidence.id)
        math_state = session.query(CurrentLearningState).filter_by(state_type="active_difficulty").one()
        science = _next_validated_evidence(
            session,
            student=student,
            subject="SCIENCE",
            concept_ref="plant_cells",
            dimensions=_dimensions(understanding="demonstrated", independence="independent"),
        )

        apply_evidence_to_current_state(session, evidence_id=science.id)

        assert math_state.status == "ACTIVE"
        assert math_state.subject == "MATH"


def test_resolved_and_expired_states_stay_historical_and_never_enter_tutor_selection(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        evidence, student = _validated_evidence(
            session,
            event_type="strategy_outcome",
            dimensions=_dimensions(strategy_effectiveness="helped"),
        )
        strategy = next(
            state
            for state in apply_evidence_to_current_state(session, evidence_id=evidence.id)
            if state.state_type == "recent_strategy_success"
        )
        resolution = _next_validated_evidence(
            session,
            student=student,
            dimensions=_dimensions(understanding="demonstrated", independence="independent"),
        )
        difficulty = _next_validated_evidence(
            session,
            student=student,
            event_type="incorrect_attempt",
            dimensions=_dimensions(understanding="partial", independence="substantial_support"),
            relationship="insufficient",
        )
        apply_evidence_to_current_state(session, evidence_id=difficulty.id)
        active_difficulty = session.query(CurrentLearningState).filter_by(state_type="active_difficulty").one()
        apply_evidence_to_current_state(session, evidence_id=resolution.id)

        expired = expire_current_states(session, now=strategy.expires_at + timedelta(seconds=1))
        selected = select_relevant_intelligence(
            session,
            student_id=student.id,
            subject="MATH",
            question="Can you help with equivalent fractions?",
        )

        assert expired == 1
        assert strategy.status == "EXPIRED"
        assert active_difficulty.status == "RESOLVED"
        assert session.get(CurrentLearningState, strategy.id) is not None
        assert session.get(CurrentLearningState, active_difficulty.id) is not None
        assert not [item for item in selected if item.source_kind == "current_state"]


def test_same_evidence_retry_is_idempotent_and_never_creates_patterns_cards_or_decisions(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        evidence, _ = _validated_evidence(
            session,
            dimensions=_dimensions(understanding="not_demonstrated", independence="substantial_support"),
        )

        first = apply_evidence_to_current_state(session, evidence_id=evidence.id)
        second = apply_evidence_to_current_state(session, evidence_id=evidence.id)

        assert {state.id for state in first} == {state.id for state in second}
        assert session.query(CurrentLearningState).count() == len(first)
        assert session.query(LearnerPattern).count() == 0
        assert session.query(LearnerIntelligenceCard).count() == 0
        assert session.query(DecisionView).count() == 0


def test_changed_state_policy_rebuilds_a_new_historical_version_without_rewriting_evidence(
    factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with factory.begin() as session:
        evidence, _ = _validated_evidence(
            session,
            dimensions=_dimensions(understanding="not_demonstrated", independence="substantial_support"),
        )
        original = apply_evidence_to_current_state(session, evidence_id=evidence.id)

        monkeypatch.setattr(current_state_module, "CURRENT_STATE_POLICY_VERSION", "current-state-policy-v2")
        rebuilt = apply_evidence_to_current_state(session, evidence_id=evidence.id)

        assert {state.id for state in original}.isdisjoint({state.id for state in rebuilt})
        assert session.get(LearningEvidence, evidence.id) is not None
        assert {state.policy_version for state in original} == {"current-state-policy-v1"}
        assert {state.policy_version for state in rebuilt} == {"current-state-policy-v2"}
