"""Deterministic TASK-025 decision-view contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.current_state import CURRENT_STATE_POLICY_VERSION
from services.intelligence.core import consolidate_student_history
from services.intelligence.decisions import (
    DECISION_VIEW_POLICY_VERSION,
    DecisionViewPolicy,
    derive_decision_views,
)
from services.intelligence.patterns import PATTERN_POLICY_VERSION
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
    reason="PostgreSQL DATABASE_URL is required for Decision View tests",
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


def _seed(session: Session) -> tuple[Student, IntelligenceProcessingRun]:
    user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id)
    session.add(student)
    session.flush()
    run = IntelligenceProcessingRun(
        student_id=student.id,
        rubric_version="evidence-rubric-v1",
        policy_version="session-consolidation-policy-v1",
        scope={"fixture": True},
    )
    session.add(run)
    session.flush()
    return student, run


def _evidence(
    session: Session,
    *,
    student: Student,
    run: IntelligenceProcessingRun,
    dimensions: dict[str, str],
    subject: str = "MATH",
    concept: str = "fractions",
    event_type: str = "learning_attempt",
    relationship: str = "supports",
    task_ref: str = "task-one",
    observed_outcome: str | None = None,
    created_at: datetime | None = None,
) -> LearningEvidence:
    occurred_at = created_at or datetime.now(UTC)
    learning_session = LearningSession(student_id=student.id, subject=subject, status="CLOSED", closed_at=occurred_at)
    session.add(learning_session)
    session.flush()
    payload: dict[str, object] = {"task_ref": task_ref, "context_ref": "math_practice"}
    if observed_outcome is not None:
        payload["observed_student_outcome"] = observed_outcome
        payload["strategy_key"] = "number_line"
    candidate = CandidateEvent(
        session_id=learning_session.id,
        message_id=None,
        event_type=event_type,
        concept_ref=concept,
        signal="fixture_signal",
        payload=payload,
        created_at=occurred_at,
    )
    session.add(candidate)
    session.flush()
    event = LearningEvent(
        processing_run_id=run.id,
        session_id=learning_session.id,
        candidate_event_id=candidate.id,
        subject=subject,
        concept_ref=concept,
        event_type=event_type,
        description="Validated fixture evidence.",
        source_message_id=None,
    )
    session.add(event)
    session.flush()
    evidence = LearningEvidence(
        event_id=event.id,
        concept_ref=concept,
        dimensions=dimensions,
        relationship=relationship,
        source_ref=f"fixture:{candidate.id}",
    )
    session.add(evidence)
    session.flush()
    return evidence


def _reprocessed_evidence(
    session: Session,
    *,
    source: LearningEvidence,
    student: Student,
    dimensions: dict[str, str],
    created_at: datetime,
    relationship: str = "improvement",
    concept: str | None = None,
) -> tuple[LearningEvidence, IntelligenceProcessingRun]:
    source_event = session.get(LearningEvent, source.event_id)
    assert source_event is not None
    run = IntelligenceProcessingRun(
        student_id=student.id,
        rubric_version="evidence-rubric-v2",
        policy_version="session-consolidation-policy-v2",
        scope={"reprocesses_event_id": str(source_event.id)},
        status="COMPLETED",
        created_at=created_at,
    )
    session.add(run)
    session.flush()
    event = LearningEvent(
        processing_run_id=run.id,
        session_id=source_event.session_id,
        candidate_event_id=source_event.candidate_event_id,
        subject=source_event.subject,
        concept_ref=concept or source_event.concept_ref,
        event_type=source_event.event_type,
        description="Reprocessed validated fixture evidence.",
        source_message_id=source_event.source_message_id,
    )
    session.add(event)
    session.flush()
    evidence = LearningEvidence(
        event_id=event.id,
        concept_ref=concept or source.concept_ref,
        dimensions=dimensions,
        relationship=relationship,
        source_ref=source.source_ref,
    )
    session.add(evidence)
    session.flush()
    return evidence, run


def _state(
    student: Student,
    run: IntelligenceProcessingRun,
    *,
    concept: str = "fractions",
    subject: str = "MATH",
    state_type: str = "active_difficulty",
    status: str = "ACTIVE",
    expires_at: datetime | None = None,
) -> CurrentLearningState:
    return CurrentLearningState(
        student_id=student.id,
        processing_run_id=run.id,
        subject=subject,
        state_type=state_type,
        concept_ref=concept,
        detail="Validated current source fact.",
        status=status,
        evidence_refs=[],
        policy_version=CURRENT_STATE_POLICY_VERSION,
        expires_at=expires_at,
    )


def _pattern(
    student: Student,
    run: IntelligenceProcessingRun,
    *,
    concept: str = "fractions",
    status: str = "STABLE",
) -> LearnerPattern:
    scope = {"scope_type": "concept", "subject": "MATH", "concept_ref": concept}
    return LearnerPattern(
        student_id=student.id,
        processing_run_id=run.id,
        pattern_type="support_need",
        pattern_key=f"support_need:{concept}",
        scope=scope,
        scope_key=json.dumps(scope, sort_keys=True, separators=(",", ":")),
        policy_version=PATTERN_POLICY_VERSION,
        status=status,
        support_count=3,
        counter_count=0,
        detail="Validated historical support pattern.",
    )


def _views(session: Session, student: Student, run: IntelligenceProcessingRun, *, subject: str = "MATH", concept: str = "fractions", policy: DecisionViewPolicy | None = None) -> dict[str, DecisionView]:
    return {
        view.view_type: view
        for view in derive_decision_views(
            session,
            student_id=student.id,
            processing_run_id=run.id,
            subject=subject,
            concept_ref=concept,
            policy=policy,
        )
    }


def test_no_evidence_is_insufficient_and_creates_only_derived_views(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student, run = _seed(session)
        views = _views(session, student, run)

    assert views["learning_status"].conclusion == "INSUFFICIENT_EVIDENCE"
    assert views["learning_status"].confidence == "LOW"
    assert views["retention"].conclusion == "INSUFFICIENT_EVIDENCE"
    assert all(view.policy_version == DECISION_VIEW_POLICY_VERSION for view in views.values())


def test_candidate_adapter_cannot_write_a_decision_view_without_task021_evidence(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, _ = _seed(session)
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="CLOSED")
        session.add(learning_session)
        session.flush()
        session.add(
            CandidateEvent(
                session_id=learning_session.id,
                message_id=None,
                event_type="independent_success",
                concept_ref="fractions",
                signal="solved_independently",
                payload={},
            )
        )
        session.flush()
        consolidate_student_history(session, student_id=student.id)

        assert session.query(DecisionView).count() == 0


def test_partial_and_one_independent_evidence_are_developing_not_high_confidence(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student, run = _seed(session)
        _evidence(session, student=student, run=run, dimensions=_dimensions(understanding="partial", independence="light_support"))
        guided = _views(session, student, run)
        assert guided["learning_status"].conclusion == "DEVELOPING"
        assert guided["learning_status"].confidence == "LOW"

        _evidence(
            session, student=student, run=run,
            dimensions=_dimensions(understanding="strong_demonstration", independence="independent"),
            relationship="improvement", task_ref="task-two",
        )
        improved = _views(session, student, run)

    assert improved["learning_status"].conclusion == "DEVELOPING"
    assert improved["learning_status"].confidence != "HIGH"
    assert improved["independence"].conclusion == "STRONG"


def test_diverse_demonstrated_evidence_is_strong_with_higher_confidence(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student, run = _seed(session)
        for index in range(3):
            _evidence(
                session, student=student, run=run,
                dimensions=_dimensions(understanding="demonstrated", independence="independent"),
                relationship="improvement", task_ref=f"task-{index}",
            )
        views = _views(session, student, run)

    assert views["learning_status"].conclusion == "STRONG"
    assert views["learning_status"].confidence == "HIGH"
    assert "3 validated" in views["learning_status"].explanation.casefold()


def test_reprocessing_versions_of_one_observation_count_once_and_keep_selected_provenance(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, base_run = _seed(session)
        original = _evidence(
            session,
            student=student,
            run=base_run,
            dimensions=_dimensions(understanding="strong_demonstration", independence="independent"),
        )
        second, second_run = _reprocessed_evidence(
            session,
            source=original,
            student=student,
            dimensions=_dimensions(understanding="strong_demonstration", independence="independent"),
            created_at=datetime.now(UTC) + timedelta(seconds=1),
        )
        latest, latest_run = _reprocessed_evidence(
            session,
            source=original,
            student=student,
            dimensions=_dimensions(understanding="strong_demonstration", independence="independent"),
            created_at=datetime.now(UTC) + timedelta(seconds=2),
        )
        first = _views(session, student, latest_run)
        second_pass = _views(session, student, latest_run)

        status = first["learning_status"]
        assert status.conclusion == "DEVELOPING"
        assert status.confidence == "LOW"
        assert status.evidence_ids == [str(latest.id)]
        assert status.source_versions["evidence_processing_run_ids"] == [str(latest_run.id)]
        assert first["learning_status"].id == second_pass["learning_status"].id
        assert session.query(LearningEvidence).count() == 3
        assert session.get(LearningEvidence, original.id) is not None
        assert session.get(LearningEvidence, second.id) is not None
        assert session.get(LearningEvidence, latest.id) is not None
        assert session.query(CurrentLearningState).count() == 0
        assert session.query(LearnerPattern).count() == 0
        assert session.query(LearnerIntelligenceCard).count() == 0


def test_newer_reprocessed_interpretation_replaces_only_the_selected_view_input(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, base_run = _seed(session)
        older = _evidence(
            session,
            student=student,
            run=base_run,
            dimensions=_dimensions(understanding="partial", independence="light_support"),
        )
        newer, newer_run = _reprocessed_evidence(
            session,
            source=older,
            student=student,
            dimensions=_dimensions(understanding="strong_demonstration", independence="independent"),
            created_at=datetime.now(UTC) + timedelta(seconds=1),
            concept="decimals",
        )
        stale_concept = _views(session, student, newer_run)
        views = _views(session, student, newer_run, concept="decimals")

    assert views["independence"].conclusion == "STRONG"
    assert views["learning_status"].evidence_ids == [str(newer.id)]
    assert str(older.id) not in views["learning_status"].evidence_ids
    assert stale_concept["learning_status"].conclusion == "INSUFFICIENT_EVIDENCE"
    assert stale_concept["learning_status"].evidence_ids == []


def test_active_state_and_current_independence_outrank_old_support_history(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student, run = _seed(session)
        active = _state(student, run)
        old_pattern = _pattern(student, run)
        session.add_all((active, old_pattern))
        needs_attention = _views(session, student, run)
        assert needs_attention["learning_status"].conclusion == "NEEDS_ATTENTION"

        active.status = "RESOLVED"
        independent = _evidence(
            session, student=student, run=run,
            dimensions=_dimensions(understanding="strong_demonstration", independence="independent"),
            relationship="improvement", task_ref="fresh-independent",
        )
        updated = _views(session, student, run)

    assert updated["learning_status"].conclusion == "DEVELOPING"
    assert str(old_pattern.id) in updated["learning_status"].pattern_ids
    assert str(independent.id) in updated["learning_status"].evidence_ids


def test_resolved_expired_or_weakening_sources_do_not_act_as_current_support(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student, run = _seed(session)
        expired = _state(student, run, expires_at=datetime.now(UTC) - timedelta(seconds=1))
        resolved = _pattern(student, run, status="RESOLVED")
        weakening = _pattern(student, run, concept="decimals", status="WEAKENING")
        session.add_all((expired, resolved, weakening))
        views = _views(session, student, run)

    status = views["learning_status"]
    assert status.conclusion == "INSUFFICIENT_EVIDENCE"
    assert status.state_ids == []
    assert status.pattern_ids == []


def test_retention_requires_a_test_and_later_recovery_improves_it(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student, run = _seed(session)
        _evidence(session, student=student, run=run, dimensions=_dimensions(retention="not_tested"))
        assert _views(session, student, run)["retention"].conclusion == "INSUFFICIENT_EVIDENCE"
        _evidence(session, student=student, run=run, dimensions=_dimensions(retention="retrieval_failed"), relationship="retention_failure", task_ref="review-one")
        assert _views(session, student, run)["retention"].conclusion == "NEEDS_ATTENTION"
        _evidence(session, student=student, run=run, dimensions=_dimensions(retention="rapid_recovery"), relationship="improvement", task_ref="review-two")
        recovered = _views(session, student, run)["retention"]

    assert recovered.conclusion == "DEVELOPING"


def test_strategy_requires_observable_outcome_and_conflict_lowers_confidence(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student, run = _seed(session)
        _evidence(session, student=student, run=run, event_type="strategy_applied", dimensions=_dimensions(strategy_effectiveness="helped"))
        assert _views(session, student, run)["strategy_effectiveness"].conclusion == "INSUFFICIENT_EVIDENCE"
        for index in range(3):
            _evidence(session, student=student, run=run, event_type="strategy_outcome", observed_outcome="Student applied the number line.", dimensions=_dimensions(strategy_effectiveness="helped"), task_ref=f"strategy-{index}")
        positive = _views(session, student, run)["strategy_effectiveness"]
        positive_conclusion = positive.conclusion
        positive_confidence = positive.confidence
        _evidence(session, student=student, run=run, event_type="strategy_outcome", observed_outcome="Student remained unable to apply it.", dimensions=_dimensions(strategy_effectiveness="ineffective"), task_ref="strategy-conflict")
        conflicting = _views(session, student, run)["strategy_effectiveness"]

    assert positive_conclusion == "STRONG"
    assert conflicting.conclusion == "DEVELOPING"
    assert conflicting.confidence != positive_confidence


def test_subject_provenance_idempotency_and_policy_history(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student, run = _seed(session)
        evidence = _evidence(session, student=student, run=run, dimensions=_dimensions(understanding="partial", independence="light_support"))
        state = _state(student, run)
        pattern = _pattern(student, run)
        session.add_all((state, pattern))
        first = _views(session, student, run)
        second = _views(session, student, run)
        science = _views(session, student, run, subject="SCIENCE")
        revised = _views(session, student, run, policy=DecisionViewPolicy(version="decision-view-policy-v2"))

        assert first["learning_status"].id == second["learning_status"].id
        assert first["learning_status"].evidence_ids == [str(evidence.id)]
        assert first["learning_status"].state_ids == [str(state.id)]
        assert first["learning_status"].pattern_ids == [str(pattern.id)]
        assert "validated" in first["learning_status"].explanation.casefold()
        assert science["learning_status"].conclusion == "INSUFFICIENT_EVIDENCE"
        assert revised["learning_status"].id != first["learning_status"].id
        assert session.query(DecisionView).filter_by(policy_version=DECISION_VIEW_POLICY_VERSION).count() == 8
        assert session.query(DecisionView).filter_by(policy_version="decision-view-policy-v2").count() == 4
        assert session.query(LearningEvidence).count() == 1
        assert session.query(CurrentLearningState).count() == 1
        assert session.query(LearnerPattern).count() == 1
        assert session.query(LearnerIntelligenceCard).count() == 0
