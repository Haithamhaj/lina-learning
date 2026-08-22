"""Deterministic contracts for the TASK-023 Pattern Engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import services.intelligence.patterns as patterns_module
from services.intelligence.patterns import (
    PATTERN_POLICY_VERSION,
    PatternPolicyError,
    apply_evidence_to_patterns,
    apply_processing_run_patterns,
)
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CandidateEvent,
    IntelligenceProcessingRun,
    LearnerIntelligenceCard,
    LearnerPattern,
    LearningEvidence,
    LearningEvent,
    LearningSession,
    PatternEvidence,
    Student,
    User,
    DecisionView,
)


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Pattern Engine tests",
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


def _student(session: Session) -> Student:
    user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id)
    session.add(student)
    session.flush()
    return student


def _evidence(
    session: Session,
    *,
    student: Student,
    concept: str = "equivalent_fractions",
    event_type: str = "learning_attempt",
    dimensions: dict[str, str] | None = None,
    relationship: str = "supports",
    created_at: datetime | None = None,
    task_ref: str | None = None,
    context_ref: str | None = None,
    strategy_key: str | None = None,
    observed_outcome: str | None = None,
    signal: str = "fixture_signal",
) -> LearningEvidence:
    occurred_at = created_at or datetime(2026, 8, 22, 12, tzinfo=UTC)
    learning_session = LearningSession(
        student_id=student.id,
        subject="MATH",
        status="CLOSED",
        closed_at=occurred_at,
    )
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
            "prompt_version": "fixture-v1",
            "provider": "fixture",
            "model": "fixture",
        },
    )
    session.add(run)
    session.flush()
    payload = {"task_ref": task_ref or f"task:{concept}", "context_ref": context_ref or "math_practice"}
    if strategy_key:
        payload["strategy_key"] = strategy_key
    if observed_outcome:
        payload["observed_student_outcome"] = observed_outcome
    candidate = CandidateEvent(
        session_id=learning_session.id,
        message_id=None,
        event_type=event_type,
        concept_ref=concept,
        signal=signal,
        payload=payload,
        created_at=occurred_at,
    )
    session.add(candidate)
    session.flush()
    event = LearningEvent(
        processing_run_id=run.id,
        session_id=learning_session.id,
        candidate_event_id=candidate.id,
        subject="MATH",
        concept_ref=concept,
        event_type=event_type,
        description="Validated source-grounded fixture event.",
        source_message_id=None,
    )
    session.add(event)
    session.flush()
    evidence = LearningEvidence(
        event_id=event.id,
        concept_ref=concept,
        dimensions=dimensions or _dimensions(),
        relationship=relationship,
        source_ref=f"fixture:{event.id}",
    )
    session.add(evidence)
    session.flush()
    return evidence


def _support() -> dict[str, str]:
    return _dimensions(understanding="partial", independence="substantial_support")


def _independent() -> dict[str, str]:
    return _dimensions(understanding="strong_demonstration", independence="independent")


def _concept_pattern(session: Session) -> LearnerPattern:
    return session.query(LearnerPattern).filter_by(pattern_type="support_need").one()


def _scope_pattern(session: Session, *, scope_type: str) -> LearnerPattern:
    return (
        session.query(LearnerPattern)
        .filter_by(pattern_type="support_need")
        .filter(LearnerPattern.scope["scope_type"].astext == scope_type)
        .one()
    )


def _scope_support(
    session: Session,
    *,
    student: Student,
    concept: str,
    context: str,
    task: str,
    occurred_at: datetime,
) -> LearningEvidence:
    return _evidence(
        session,
        student=student,
        concept=concept,
        dimensions=_support(),
        context_ref=context,
        task_ref=task,
        created_at=occurred_at,
    )


def _scope_counter(
    session: Session,
    *,
    student: Student,
    concept: str,
    task: str,
    occurred_at: datetime,
) -> LearningEvidence:
    return _evidence(
        session,
        student=student,
        concept=concept,
        dimensions=_independent(),
        relationship="improvement",
        task_ref=task,
        created_at=occurred_at,
    )


def test_one_evidence_creates_candidate_never_active_or_stable(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        evidence = _evidence(session, student=student, dimensions=_support())

        patterns = apply_evidence_to_patterns(session, evidence_id=evidence.id)

        assert [pattern.status for pattern in patterns] == ["CANDIDATE"]
        assert _concept_pattern(session).support_count == 1


def test_repeated_comparable_support_promotes_candidate_to_active(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        first = _evidence(session, student=student, dimensions=_support())
        second = _evidence(session, student=student, dimensions=_support(), created_at=datetime(2026, 8, 23, 12, tzinfo=UTC))

        apply_evidence_to_patterns(session, evidence_id=first.id)
        patterns = apply_evidence_to_patterns(session, evidence_id=second.id)

        assert _concept_pattern(session).status == "ACTIVE"
        assert any(pattern.status == "ACTIVE" for pattern in patterns)


def test_diverse_delayed_support_promotes_active_to_stable(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        evidence = [
            _evidence(session, student=student, dimensions=_support(), task_ref="fraction_visuals", created_at=datetime(2026, 8, 1, 12, tzinfo=UTC)),
            _evidence(session, student=student, dimensions=_support(), task_ref="fraction_number_line", created_at=datetime(2026, 8, 8, 12, tzinfo=UTC)),
            _evidence(session, student=student, dimensions=_support(), task_ref="fraction_word_problem", created_at=datetime(2026, 8, 20, 12, tzinfo=UTC)),
        ]

        for item in evidence:
            apply_evidence_to_patterns(session, evidence_id=item.id, now=datetime(2026, 8, 22, 12, tzinfo=UTC))

        assert _concept_pattern(session).status == "STABLE"


def test_near_identical_same_session_evidence_does_not_create_strong_diversity(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        evidence = [
            _evidence(session, student=student, dimensions=_support(), task_ref="same_task"),
            _evidence(session, student=student, dimensions=_support(), task_ref="same_task"),
            _evidence(session, student=student, dimensions=_support(), task_ref="same_task"),
        ]
        for item in evidence:
            apply_evidence_to_patterns(session, evidence_id=item.id)

        assert _concept_pattern(session).status != "STABLE"


def test_recent_strong_improvement_weakens_old_support_pattern(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        for day in (1, 4, 8):
            apply_evidence_to_patterns(session, evidence_id=_evidence(session, student=student, dimensions=_support(), task_ref=f"old:{day}", created_at=datetime(2026, 7, day, 12, tzinfo=UTC)).id)
        improvement = _evidence(session, student=student, dimensions=_independent(), relationship="improvement", task_ref="recent:success", created_at=datetime(2026, 8, 22, 12, tzinfo=UTC))

        apply_evidence_to_patterns(session, evidence_id=improvement.id, now=datetime(2026, 8, 22, 12, tzinfo=UTC))

        assert _concept_pattern(session).status == "WEAKENING"


def test_recent_independent_counter_evidence_resolves_and_preserves_links(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        supports = [_evidence(session, student=student, dimensions=_support(), task_ref=f"old:{day}", created_at=datetime(2026, 7, day, 12, tzinfo=UTC)) for day in (1, 4, 8)]
        for item in supports:
            apply_evidence_to_patterns(session, evidence_id=item.id)
        counters = [_evidence(session, student=student, dimensions=_independent(), relationship="improvement", task_ref=f"new:{day}", created_at=datetime(2026, 8, day, 12, tzinfo=UTC)) for day in (20, 22)]
        for item in counters:
            apply_evidence_to_patterns(session, evidence_id=item.id, now=datetime(2026, 8, 22, 13, tzinfo=UTC))

        pattern = _concept_pattern(session)
        assert pattern.status == "RESOLVED"
        assert session.query(PatternEvidence).filter_by(pattern_id=pattern.id).count() == 5
        assert {link.relationship for link in session.query(PatternEvidence).filter_by(pattern_id=pattern.id)} == {"supports", "improvement"}
        assert pattern.first_detected_at is not None
        assert pattern.last_supported_at is not None
        assert pattern.last_challenged_at is not None


def test_resolved_patterns_are_not_runtime_active_but_remain_queryable(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        supports = [_evidence(session, student=student, dimensions=_support(), task_ref=f"old:{day}") for day in (1, 2)]
        counters = [_evidence(session, student=student, dimensions=_independent(), relationship="improvement", task_ref=f"new:{day}") for day in (1, 2)]
        for item in supports + counters:
            apply_evidence_to_patterns(session, evidence_id=item.id)
        pattern = _concept_pattern(session)

        assert pattern.status == "RESOLVED"
        assert session.query(LearnerPattern).filter(LearnerPattern.status.in_(("ACTIVE", "STABLE", "WEAKENING"))).count() == 0
        assert session.get(LearnerPattern, pattern.id) is not None


def test_one_recurrence_signal_does_not_reactivate_resolved_pattern(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        for item in [
            _evidence(session, student=student, dimensions=_support(), task_ref="a"),
            _evidence(session, student=student, dimensions=_support(), task_ref="b"),
            _evidence(session, student=student, dimensions=_independent(), relationship="improvement", task_ref="c"),
            _evidence(session, student=student, dimensions=_independent(), relationship="improvement", task_ref="d"),
        ]:
            apply_evidence_to_patterns(session, evidence_id=item.id)
        recurrence = _evidence(session, student=student, dimensions=_support(), task_ref="new-signal")

        patterns = apply_evidence_to_patterns(session, evidence_id=recurrence.id)

        assert _concept_pattern(session).status == "CANDIDATE"
        assert all(pattern.status not in {"ACTIVE", "STABLE"} for pattern in patterns)


def test_fresh_repeated_recurrence_reactivates_through_normal_lifecycle(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        for item in [
            _evidence(session, student=student, dimensions=_support(), task_ref="a"),
            _evidence(session, student=student, dimensions=_support(), task_ref="b"),
            _evidence(session, student=student, dimensions=_independent(), relationship="improvement", task_ref="c"),
            _evidence(session, student=student, dimensions=_independent(), relationship="improvement", task_ref="d"),
        ]:
            apply_evidence_to_patterns(session, evidence_id=item.id)
        for task in ("new-a", "new-b"):
            apply_evidence_to_patterns(session, evidence_id=_evidence(session, student=student, dimensions=_support(), task_ref=task).id)

        assert _concept_pattern(session).status == "ACTIVE"


def test_strategy_selection_without_observable_outcome_creates_no_strategy_pattern(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        evidence = _evidence(session, student=student, event_type="strategy_outcome", strategy_key="decompose_word_problem")

        assert apply_evidence_to_patterns(session, evidence_id=evidence.id) == []
        assert session.query(LearnerPattern).count() == 0


def test_specific_repeated_misconception_promotes_active_then_stable(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        signal = "adds_denominators_when_adding_fractions"
        first = _evidence(
            session,
            student=student,
            event_type="misconception_signal",
            dimensions=_support(),
            signal=signal,
            task_ref="fraction_sum_a",
            created_at=datetime(2026, 7, 1, 12, tzinfo=UTC),
        )
        second = _evidence(
            session,
            student=student,
            event_type="misconception_signal",
            dimensions=_support(),
            signal=signal,
            task_ref="fraction_sum_b",
            created_at=datetime(2026, 7, 8, 12, tzinfo=UTC),
        )
        third = _evidence(
            session,
            student=student,
            event_type="misconception_signal",
            dimensions=_support(),
            signal=signal,
            task_ref="fraction_sum_c",
            created_at=datetime(2026, 7, 20, 12, tzinfo=UTC),
        )

        apply_evidence_to_patterns(session, evidence_id=first.id, now=datetime(2026, 7, 1, 13, tzinfo=UTC))
        apply_evidence_to_patterns(session, evidence_id=second.id, now=datetime(2026, 7, 8, 13, tzinfo=UTC))
        pattern = session.query(LearnerPattern).filter_by(
            pattern_type="misconception_recurrence",
            pattern_key=f"misconception:{signal}",
        ).one()
        assert pattern.status == "ACTIVE"

        apply_evidence_to_patterns(session, evidence_id=third.id, now=datetime(2026, 7, 20, 13, tzinfo=UTC))

        assert pattern.status == "STABLE"


def test_specific_recent_counter_evidence_weakens_only_its_misconception(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        target = "adds_denominators_when_adding_fractions"
        unrelated = "treats_larger_denominator_as_larger_fraction"
        for signal in (target, unrelated):
            for day, task in ((1, "a"), (8, "b"), (20, "c")):
                apply_evidence_to_patterns(
                    session,
                    evidence_id=_evidence(
                        session,
                        student=student,
                        event_type="misconception_signal",
                        dimensions=_support(),
                        signal=signal,
                        task_ref=f"{signal}:{task}",
                        created_at=datetime(2026, 7, day, 12, tzinfo=UTC),
                    ).id,
                    now=datetime(2026, 7, 20, 13, tzinfo=UTC),
                )
        counter = _evidence(
            session,
            student=student,
            event_type="independent_success",
            dimensions=_independent(),
            relationship="improvement",
            signal=target,
            task_ref="correct_fraction_sum",
            created_at=datetime(2026, 8, 22, 12, tzinfo=UTC),
        )

        apply_evidence_to_patterns(session, evidence_id=counter.id, now=datetime(2026, 8, 22, 13, tzinfo=UTC))

        patterns = {
            pattern.pattern_key: pattern
            for pattern in session.query(LearnerPattern).filter_by(pattern_type="misconception_recurrence")
        }
        assert patterns[f"misconception:{target}"].status == "WEAKENING"
        assert patterns[f"misconception:{target}"].counter_count == 1
        assert patterns[f"misconception:{unrelated}"].status == "STABLE"
        assert patterns[f"misconception:{unrelated}"].counter_count == 0


def test_sufficient_specific_fresh_counter_evidence_resolves_exact_misconception(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        signal = "adds_denominators_when_adding_fractions"
        for day, task in ((1, "a"), (8, "b"), (20, "c")):
            apply_evidence_to_patterns(
                session,
                evidence_id=_evidence(
                    session,
                    student=student,
                    event_type="misconception_signal",
                    dimensions=_support(),
                    signal=signal,
                    task_ref=task,
                    created_at=datetime(2026, 7, day, 12, tzinfo=UTC),
                ).id,
            )
        counters = [
            _evidence(
                session,
                student=student,
                event_type="independent_success",
                dimensions=_independent(),
                relationship="improvement",
                signal=signal,
                task_ref=f"resolved:{day}",
                created_at=datetime(2026, 8, day, 12, tzinfo=UTC),
            )
            for day in (20, 22)
        ]

        for counter in counters:
            apply_evidence_to_patterns(session, evidence_id=counter.id, now=datetime(2026, 8, 22, 13, tzinfo=UTC))

        pattern = session.query(LearnerPattern).filter_by(
            pattern_type="misconception_recurrence",
            pattern_key=f"misconception:{signal}",
        ).one()
        assert pattern.status == "RESOLVED"
        assert pattern.counter_count == 2
        assert session.query(PatternEvidence).filter_by(pattern_id=pattern.id).count() == 5


def test_ambiguous_independent_success_does_not_create_generic_misconception_counter(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        signal = "adds_denominators_when_adding_fractions"
        for task in ("a", "b"):
            apply_evidence_to_patterns(
                session,
                evidence_id=_evidence(
                    session,
                    student=student,
                    event_type="misconception_signal",
                    dimensions=_support(),
                    signal=signal,
                    task_ref=task,
                ).id,
            )
        ambiguous = _evidence(
            session,
            student=student,
            event_type="independent_success",
            dimensions=_independent(),
            relationship="improvement",
            signal="solved_independently",
        )

        apply_evidence_to_patterns(session, evidence_id=ambiguous.id)

        pattern = session.query(LearnerPattern).filter_by(
            pattern_type="misconception_recurrence",
            pattern_key=f"misconception:{signal}",
        ).one()
        assert pattern.status == "ACTIVE"
        assert pattern.counter_count == 0
        assert session.query(LearnerPattern).filter_by(
            pattern_type="misconception_recurrence",
            pattern_key="misconception:observed",
        ).count() == 0


def test_valid_strategy_outcome_supports_and_contradiction_weakens_strategy_pattern(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        valid = _evidence(session, student=student, event_type="strategy_outcome", strategy_key="decompose_word_problem", observed_outcome="Student completed a new problem independently", dimensions=_dimensions(strategy_effectiveness="enabled_independent_success", understanding="demonstrated", independence="independent"))
        contradict = _evidence(session, student=student, event_type="strategy_outcome", strategy_key="decompose_word_problem", observed_outcome="Student remained unable to proceed", dimensions=_dimensions(strategy_effectiveness="ineffective"), relationship="contradicts")

        apply_evidence_to_patterns(session, evidence_id=valid.id)
        apply_evidence_to_patterns(session, evidence_id=contradict.id)

        pattern = session.query(LearnerPattern).filter_by(pattern_type="strategy_effectiveness").one()
        assert pattern.status == "WEAKENING"
        assert pattern.counter_count == 1


def test_scope_starts_concept_specific_then_broadens_only_across_diverse_math_concepts(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        first = _evidence(session, student=student, concept="equivalent_fractions", dimensions=_support(), context_ref="math_word_problems")
        apply_evidence_to_patterns(session, evidence_id=first.id)
        concept_pattern = _concept_pattern(session)
        assert concept_pattern.scope["scope_type"] == "concept"
        for concept in ("decimal_place_value", "ratio_reasoning"):
            apply_evidence_to_patterns(session, evidence_id=_evidence(session, student=student, concept=concept, dimensions=_support(), context_ref="math_word_problems", task_ref=concept).id)

        broader = session.query(LearnerPattern).filter_by(pattern_type="support_need").filter(LearnerPattern.scope["scope_type"].astext == "context").one()
        assert broader.scope["context_ref"] == "math_word_problems"
        assert session.query(LearnerPattern).filter(LearnerPattern.scope["scope_type"].astext == "global").count() == 0


def test_one_concept_and_near_identical_tasks_remain_concept_scoped(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        for day in (1, 8, 20):
            apply_evidence_to_patterns(
                session,
                evidence_id=_scope_support(
                    session,
                    student=student,
                    concept="equivalent_fractions",
                    context="math_word_problems",
                    task="same_fraction_prompt",
                    occurred_at=datetime(2026, 7, day, 12, tzinfo=UTC),
                ).id,
                now=datetime(2026, 7, 20, 13, tzinfo=UTC),
            )

        assert session.query(LearnerPattern).filter(
            LearnerPattern.scope["scope_type"].astext.in_(("context", "subject", "cross_subject", "global"))
        ).count() == 0


def test_multiple_concepts_from_one_worksheet_do_not_create_context_generalization(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student = _student(session)
        for day, concept in ((1, "equivalent_fractions"), (8, "decimal_place_value"), (15, "ratio_reasoning")):
            apply_evidence_to_patterns(
                session,
                evidence_id=_scope_support(
                    session,
                    student=student,
                    concept=concept,
                    context="math_word_problems",
                    task="shared_review_worksheet",
                    occurred_at=datetime(2026, 7, day, 12, tzinfo=UTC),
                ).id,
                now=datetime(2026, 7, 20, 13, tzinfo=UTC),
            )

        assert session.query(LearnerPattern).filter(
            LearnerPattern.scope["scope_type"].astext == "context"
        ).count() == 0


def test_context_scope_requires_three_distinct_concepts(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        for index, concept in enumerate(("equivalent_fractions", "decimal_place_value"), start=1):
            apply_evidence_to_patterns(
                session,
                evidence_id=_scope_support(
                    session,
                    student=student,
                    concept=concept,
                    context="math_word_problems",
                    task=concept,
                    occurred_at=datetime(2026, 7, index, 12, tzinfo=UTC),
                ).id,
            )
        assert session.query(LearnerPattern).filter(
            LearnerPattern.scope["scope_type"].astext == "context"
        ).count() == 0

        apply_evidence_to_patterns(
            session,
            evidence_id=_scope_support(
                session,
                student=student,
                concept="ratio_reasoning",
                context="math_word_problems",
                task="ratio_reasoning",
                occurred_at=datetime(2026, 7, 3, 12, tzinfo=UTC),
            ).id,
        )

        assert _scope_pattern(session, scope_type="context").scope["context_ref"] == "math_word_problems"


def test_subject_scope_requires_two_qualifying_contexts(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        for context, concepts in {
            "math_word_problems": ("equivalent_fractions", "decimal_place_value", "ratio_reasoning"),
            "math_visual_models": ("area_models", "number_lines", "bar_models"),
        }.items():
            for index, concept in enumerate(concepts, start=1):
                apply_evidence_to_patterns(
                    session,
                    evidence_id=_scope_support(
                        session,
                        student=student,
                        concept=concept,
                        context=context,
                        task=f"{context}:{concept}",
                        occurred_at=datetime(2026, 7, index, 12, tzinfo=UTC),
                    ).id,
                )
            if context == "math_word_problems":
                assert session.query(LearnerPattern).filter(
                    LearnerPattern.scope["scope_type"].astext == "subject"
                ).count() == 0

        assert _scope_pattern(session, scope_type="subject").scope == {"scope_type": "subject", "subject": "MATH"}


def test_resolved_concept_support_recomputes_broad_scope_without_touching_other_concepts(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student = _student(session)
        concepts = ("equivalent_fractions", "decimal_place_value", "ratio_reasoning")
        for index, concept in enumerate(concepts, start=1):
            apply_evidence_to_patterns(
                session,
                evidence_id=_scope_support(
                    session,
                    student=student,
                    concept=concept,
                    context="math_word_problems",
                    task=concept,
                    occurred_at=datetime(2026, 7, index, 12, tzinfo=UTC),
                ).id,
            )
        broad = _scope_pattern(session, scope_type="context")
        target_id = session.query(LearnerPattern).filter(
            LearnerPattern.scope["scope_type"].astext == "concept",
            LearnerPattern.scope["concept_ref"].astext == "equivalent_fractions",
        ).one().id
        other = session.query(LearnerPattern).filter(
            LearnerPattern.scope["scope_type"].astext == "concept",
            LearnerPattern.scope["concept_ref"].astext == "decimal_place_value",
        ).one()
        for day in (20, 22):
            apply_evidence_to_patterns(
                session,
                evidence_id=_scope_counter(
                    session,
                    student=student,
                    concept="equivalent_fractions",
                    task=f"independent:{day}",
                    occurred_at=datetime(2026, 8, day, 12, tzinfo=UTC),
                ).id,
                now=datetime(2026, 8, 22, 13, tzinfo=UTC),
            )

        assert session.get(LearnerPattern, target_id).status == "RESOLVED"
        assert other.status == "CANDIDATE"
        assert broad.status == "WEAKENING"


def test_recent_comparable_counter_evidence_resolves_broader_scope_and_preserves_lineage(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student = _student(session)
        context = "math_word_problems"
        for day, concept in ((1, "equivalent_fractions"), (8, "decimal_place_value"), (15, "ratio_reasoning")):
            apply_evidence_to_patterns(
                session,
                evidence_id=_scope_support(
                    session,
                    student=student,
                    concept=concept,
                    context=context,
                    task=f"support:{concept}",
                    occurred_at=datetime(2026, 7, day, 12, tzinfo=UTC),
                ).id,
                now=datetime(2026, 7, 20, 13, tzinfo=UTC),
            )
        broader = _scope_pattern(session, scope_type="context")
        assert broader.status == "STABLE"

        for day, concept in ((20, "equivalent_fractions"), (22, "decimal_place_value")):
            counter = _evidence(
                session,
                student=student,
                concept=concept,
                dimensions=_independent(),
                relationship="improvement",
                context_ref=context,
                task_ref=f"independent:{concept}",
                created_at=datetime(2026, 8, day, 12, tzinfo=UTC),
            )
            apply_evidence_to_patterns(
                session,
                evidence_id=counter.id,
                now=datetime(2026, 8, 22, 13, tzinfo=UTC),
            )

        assert broader.status == "RESOLVED"
        links = session.query(PatternEvidence).filter_by(pattern_id=broader.id).all()
        assert {link.relationship for link in links} == {"supports", "improvement"}
        assert broader.counter_count == 2


def test_one_concept_recurrence_does_not_reactivate_resolved_subject_scope(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        student = _student(session)
        contexts = {
            "math_word_problems": ("equivalent_fractions", "decimal_place_value", "ratio_reasoning"),
            "math_visual_models": ("area_models", "number_lines", "bar_models"),
        }
        for context, concepts in contexts.items():
            for index, concept in enumerate(concepts, start=1):
                apply_evidence_to_patterns(
                    session,
                    evidence_id=_scope_support(
                        session,
                        student=student,
                        concept=concept,
                        context=context,
                        task=f"{context}:{concept}",
                        occurred_at=datetime(2026, 7, index, 12, tzinfo=UTC),
                    ).id,
                )
        subject = _scope_pattern(session, scope_type="subject")
        for concepts in contexts.values():
            for concept in concepts:
                for day in (20, 22):
                    apply_evidence_to_patterns(
                        session,
                        evidence_id=_scope_counter(
                            session,
                            student=student,
                            concept=concept,
                            task=f"{concept}:independent:{day}",
                            occurred_at=datetime(2026, 8, day, 12, tzinfo=UTC),
                        ).id,
                        now=datetime(2026, 8, 22, 13, tzinfo=UTC),
                    )
        assert subject.status == "RESOLVED"

        recurrence = _scope_support(
            session,
            student=student,
            concept="equivalent_fractions",
            context="math_word_problems",
            task="fresh_recurrence",
            occurred_at=datetime(2026, 9, 1, 12, tzinfo=UTC),
        )
        apply_evidence_to_patterns(session, evidence_id=recurrence.id, now=datetime(2026, 9, 1, 13, tzinfo=UTC))

        assert subject.status == "RESOLVED"
        assert session.query(LearnerPattern).filter(
            LearnerPattern.scope["scope_type"].astext.in_(("cross_subject", "global"))
        ).count() == 0


def test_same_identity_and_retry_reject_an_uncompiled_policy_label(factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch) -> None:
    with factory.begin() as session:
        student = _student(session)
        evidence = _evidence(session, student=student, dimensions=_support())
        original = apply_evidence_to_patterns(session, evidence_id=evidence.id)
        retry = apply_evidence_to_patterns(session, evidence_id=evidence.id)

        assert [item.id for item in original] == [item.id for item in retry]
        assert session.query(LearnerPattern).count() == 1
        assert session.query(PatternEvidence).count() == 1
        monkeypatch.setattr(patterns_module, "PATTERN_POLICY_VERSION", "pattern-policy-v2")
        with pytest.raises(PatternPolicyError):
            apply_processing_run_patterns(session, processing_run_id=session.query(LearningEvent).one().processing_run_id)

        assert session.query(LearnerPattern).count() == 1
        assert {pattern.policy_version for pattern in session.query(LearnerPattern)} == {PATTERN_POLICY_VERSION}
        assert session.query(LearnerIntelligenceCard).count() == 0
        assert session.query(DecisionView).count() == 0
