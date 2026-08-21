"""Deterministic contracts for the compact TASK-024 runtime intelligence Card."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.card import (
    INTELLIGENCE_CARD_POLICY_VERSION,
    INTELLIGENCE_CARD_SCHEMA_VERSION,
    CardBudget,
    build_learner_intelligence_card,
)
from services.intelligence.current_state import CURRENT_STATE_POLICY_VERSION
from services.intelligence.patterns import PATTERN_POLICY_VERSION
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CurrentLearningState,
    DecisionView,
    IntelligenceProcessingRun,
    LearnerIntelligenceCard,
    LearnerPattern,
    LearningEvidence,
    LearningSession,
    Student,
    User,
)
from services.retrieval.service import CurrentFocus, RetrievedBlock
from services.tutor.context import TutorContextBuilder


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Intelligence Card tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE ai_executions, jobs, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _seed(session: Session) -> tuple[Student, LearningSession, IntelligenceProcessingRun]:
    user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id)
    session.add(student)
    session.flush()
    learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
    run = IntelligenceProcessingRun(
        student_id=student.id,
        rubric_version="fixture",
        policy_version="fixture",
        scope={},
    )
    session.add_all((learning_session, run))
    session.flush()
    return student, learning_session, run


def _state(
    student: Student,
    run: IntelligenceProcessingRun,
    *,
    concept: str,
    detail: str,
    state_type: str = "active_difficulty",
    status: str = "ACTIVE",
    subject: str = "MATH",
    updated_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> CurrentLearningState:
    return CurrentLearningState(
        student_id=student.id,
        processing_run_id=run.id,
        subject=subject,
        state_type=state_type,
        concept_ref=concept,
        detail=detail,
        status=status,
        evidence_refs=[],
        policy_version=CURRENT_STATE_POLICY_VERSION,
        updated_at=updated_at or datetime.now(UTC),
        expires_at=expires_at,
    )


def _pattern(
    student: Student,
    run: IntelligenceProcessingRun,
    *,
    key: str,
    detail: str,
    scope: dict[str, str],
    status: str = "ACTIVE",
    subject: str = "MATH",
    last_supported_at: datetime | None = None,
) -> LearnerPattern:
    complete_scope = {"subject": subject, **scope}
    return LearnerPattern(
        student_id=student.id,
        processing_run_id=run.id,
        pattern_type="support_need",
        pattern_key=key,
        scope=complete_scope,
        scope_key=json.dumps(complete_scope, sort_keys=True, separators=(",", ":")),
        policy_version=PATTERN_POLICY_VERSION,
        status=status,
        support_count=3,
        counter_count=0,
        detail=detail,
        last_supported_at=last_supported_at or datetime.now(UTC),
    )


def _card(session: Session, student: Student, *, question: str, focus: CurrentFocus | None = None, budget: CardBudget | None = None):
    return build_learner_intelligence_card(
        session,
        student_id=student.id,
        subject="MATH",
        question=question,
        focus=focus,
        budget=budget or CardBudget(),
    )


def test_card_includes_relevant_active_state_and_excludes_resolved_or_expired_state(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, _, run = _seed(session)
        active = _state(student, run, concept="fractions", detail="Fractions comparison needs one check.")
        resolved = _state(student, run, concept="fractions", detail="Old fractions difficulty.", status="RESOLVED")
        expired = _state(
            student,
            run,
            concept="fractions",
            detail="Expired fractions strategy note.",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        session.add_all((active, resolved, expired))
        card = _card(session, student, question="Can you help compare fractions?")

    assert [entry.source_id for entry in card.entries] == [active.id]
    assert card.schema_version == INTELLIGENCE_CARD_SCHEMA_VERSION
    assert card.policy_version == INTELLIGENCE_CARD_POLICY_VERSION


def test_card_selects_only_active_or_stable_patterns_and_ranks_narrow_scope_first(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, _, run = _seed(session)
        exact = _pattern(
            student, run, key="support_need:decimals", detail="Decimals comparison sometimes benefits from a check.",
            scope={"scope_type": "concept", "concept_ref": "decimals"}, status="ACTIVE",
        )
        context = _pattern(
            student, run, key="support_need:decimals-context", detail="Decimals comparison representation can use a check.",
            scope={"scope_type": "context", "context_ref": "decimals_comparison"}, status="ACTIVE",
        )
        subject = _pattern(
            student, run, key="support_need:decimals-subject", detail="Decimals comparison Math support history.",
            scope={"scope_type": "subject"}, status="STABLE",
        )
        excluded = [
            _pattern(student, run, key=f"support_need:decimals-{status.casefold()}", detail=f"Decimals {status} history.", scope={"scope_type": "concept", "concept_ref": "decimals"}, status=status)
            for status in ("CANDIDATE", "WEAKENING", "RESOLVED", "SUPERSEDED")
        ]
        session.add_all((exact, context, subject, *excluded))
        card = _card(session, student, question="How do I compare decimals?")

    assert [entry.source_id for entry in card.entries] == [exact.id, context.id, subject.id]
    assert [entry.source_kind for entry in card.entries] == ["recent_pattern", "recent_pattern", "stable_pattern"]
    assert card.debug.selected_source_ids == (exact.id, context.id, subject.id)


def test_explicit_question_beats_stale_focus_and_excludes_other_subject_or_unrelated_history(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, _, run = _seed(session)
        decimals = _pattern(
            student, run, key="support_need:decimals", detail="Decimals place value needs a check.",
            scope={"scope_type": "concept", "concept_ref": "decimals"}, status="STABLE",
        )
        stale_focus = _pattern(
            student, run, key="support_need:fractions", detail="Fractions support history.",
            scope={"scope_type": "concept", "concept_ref": "fractions"}, status="STABLE",
        )
        unrelated = _pattern(
            student, run, key="support_need:area", detail="Area support history.",
            scope={"scope_type": "concept", "concept_ref": "area"}, status="STABLE",
        )
        science = _pattern(
            student, run, key="support_need:decimals-science", detail="Decimals science note.",
            scope={"scope_type": "concept", "concept_ref": "decimals"}, status="STABLE", subject="SCIENCE",
        )
        session.add_all((decimals, stale_focus, unrelated, science))
        card = _card(
            session,
            student,
            question="Why does 0.4 compare differently from 0.35 in decimals?",
            focus=CurrentFocus(concept_key="fractions"),
        )

    assert [entry.source_id for entry in card.entries] == [decimals.id]


def test_stale_focus_never_enters_an_explicit_unmatched_question(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, _, run = _seed(session)
        fractions = _pattern(
            student, run, key="support_need:fractions", detail="Fractions support history.",
            scope={"scope_type": "concept", "concept_ref": "fractions"}, status="STABLE",
        )
        session.add(fractions)

        numeric = _card(
            session,
            student,
            question="What is 0.5 + 0.25?",
            focus=CurrentFocus(concept_key="fractions"),
        )
        word_problem = _card(
            session,
            student,
            question="A bus has 24 seats and 7 are empty. How many are filled?",
            focus=CurrentFocus(concept_key="fractions"),
        )

    assert numeric.entries == ()
    assert word_problem.entries == ()


@pytest.mark.parametrize("question", ("continue", "تابعي"))
def test_low_information_turn_may_use_current_focus(
    factory: sessionmaker[Session],
    question: str,
) -> None:
    with factory.begin() as session:
        student, _, run = _seed(session)
        fractions = _pattern(
            student, run, key="support_need:fractions", detail="Fractions support history.",
            scope={"scope_type": "concept", "concept_ref": "fractions"}, status="STABLE",
        )
        session.add(fractions)
        card = _card(session, student, question=question, focus=CurrentFocus(concept_key="fractions"))

    assert [entry.source_id for entry in card.entries] == [fractions.id]
    assert card.debug.selection_reasons == ("focus_fallback",)


def test_explicit_matching_fractions_question_keeps_normal_card_budget_and_provenance(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, _, run = _seed(session)
        fractions = _pattern(
            student, run, key="support_need:fractions", detail="Fractions support history.",
            scope={"scope_type": "concept", "concept_ref": "fractions"}, status="STABLE",
        )
        session.add(fractions)
        card = _card(
            session,
            student,
            question="Can you explain equivalent fractions?",
            focus=CurrentFocus(concept_key="fractions"),
            budget=CardBudget(max_entries=1, max_states=1, max_patterns=1, max_characters=200),
        )

    assert [entry.source_id for entry in card.entries] == [fractions.id]
    assert card.debug.selected_source_ids == (fractions.id,)
    assert card.debug.selection_reasons == ("exact_question_concept",)


def test_current_independent_change_outranks_broad_support_history(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, _, run = _seed(session)
        independent = _state(
            student,
            run,
            concept="fractions",
            state_type="important_recent_change",
            detail="Fractions comparison was completed independently today.",
        )
        broad = _pattern(
            student, run, key="support_need:fractions-subject", detail="Fractions support is often useful in Math.",
            scope={"scope_type": "subject"}, status="STABLE", last_supported_at=datetime.now(UTC) - timedelta(days=60),
        )
        session.add_all((independent, broad))
        card = _card(session, student, question="Please check my independent fractions solution.")

    assert [entry.source_id for entry in card.entries] == [independent.id, broad.id]
    assert card.entries[0].selection_reason == "exact_question_concept"


def test_card_ranks_before_budgeting_and_preserves_deterministic_debug_provenance(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, _, run = _seed(session)
        state = _state(student, run, concept="fractions", detail="Fractions need a concise current check.")
        stable = _pattern(
            student, run, key="support_need:fractions", detail="Fractions historical support note that must not crowd out current state.",
            scope={"scope_type": "concept", "concept_ref": "fractions"}, status="STABLE",
        )
        session.add_all((state, stable))
        budget = CardBudget(max_entries=1, max_states=1, max_patterns=1, max_characters=200)
        first = _card(session, student, question="Help with fractions please.", budget=budget)
        second = _card(session, student, question="Help with fractions please.", budget=budget)

        assert [entry.source_id for entry in first.entries] == [state.id]
        assert first.entries == second.entries
        assert first.debug.selected_source_ids == (state.id,)
        assert first.debug.selection_reasons == ("exact_question_concept",)
        assert first.debug.schema_version == INTELLIGENCE_CARD_SCHEMA_VERSION
        assert first.debug.policy_version == INTELLIGENCE_CARD_POLICY_VERSION
        assert session.query(LearnerIntelligenceCard).count() == 0
        assert session.query(DecisionView).count() == 0
        assert session.query(LearningEvidence).count() == 0
        assert session.query(CurrentLearningState).count() == 1
        assert session.query(LearnerPattern).count() == 1


class _NoopRetrieval:
    def retrieve(self, **kwargs: object) -> list[RetrievedBlock]:
        del kwargs
        return []


def test_tutor_context_receives_only_the_selected_card_slice(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, learning_session, run = _seed(session)
        selected = _state(student, run, concept="fractions", detail="Fractions current check.")
        excluded = _pattern(
            student, run, key="support_need:area", detail="Area historical note.",
            scope={"scope_type": "concept", "concept_ref": "area"}, status="STABLE",
        )
        session.add_all((selected, excluded))
        context = TutorContextBuilder(session, retrieval_service=_NoopRetrieval()).build(
            learning_session=learning_session,
            question="Please help me compare fractions.",
        )

    assert [item.source_id for item in context.intelligence] == [selected.id]
    assert context.debug.intelligence_source_ids == (selected.id,)
    assert context.debug.intelligence_card_schema_version == INTELLIGENCE_CARD_SCHEMA_VERSION
    assert context.debug.intelligence_card_policy_version == INTELLIGENCE_CARD_POLICY_VERSION
