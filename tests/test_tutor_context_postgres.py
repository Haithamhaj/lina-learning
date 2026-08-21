"""PostgreSQL contracts for TASK-017 Tutor context assembly."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.current_state import CURRENT_STATE_POLICY_VERSION
from services.intelligence.selection import select_relevant_intelligence
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CurrentLearningState,
    IntelligenceProcessingRun,
    LearnerPattern,
    LearningMessage,
    LearningSession,
    Student,
    User,
)
from services.retrieval.service import CurrentFocus, RetrievedBlock
from services.tutor.context import ContextBudget, TutorContextBuilder


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Tutor context tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE learning_messages, learning_sessions, current_learning_states, "
                "learner_patterns, intelligence_processing_runs, students, users CASCADE"
            )
        )
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


class RecordingRetrieval:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def retrieve(self, **kwargs: object) -> list[RetrievedBlock]:
        self.calls.append(kwargs)
        return [
            RetrievedBlock(
                text="A fraction names equal parts of a whole.",
                source_ref="book#page=12",
                page_number=12,
                block_type="SEMANTIC",
                score=0.0,
                semantic_key="fractions",
                semantic_type="EXPLANATION",
                concept_key="fractions",
                source_refs=("book#page=12",),
                page_numbers=(12,),
                matched=True,
            )
        ]


def _seed(session: Session) -> tuple[Student, LearningSession, IntelligenceProcessingRun]:
    user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id)
    session.add(student)
    session.flush()
    learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
    session.add(learning_session)
    run = IntelligenceProcessingRun(
        student_id=student.id,
        rubric_version="fixture",
        policy_version="fixture",
        scope={},
    )
    session.add(run)
    session.flush()
    return student, learning_session, run


def test_context_keeps_current_question_bounds_history_and_uses_task014_retrieval(
    factory: sessionmaker[Session],
) -> None:
    retrieval = RecordingRetrieval()
    with factory.begin() as session:
        student, learning_session, _ = _seed(session)
        base = datetime.now(UTC)
        for index in range(5):
            session.add(
                LearningMessage(
                    session_id=learning_session.id,
                    role="student",
                    content=f"older turn {index}",
                    payload={"concept_ref": "fractions"} if index == 4 else {},
                    created_at=base + timedelta(seconds=index),
                )
            )
        context = TutorContextBuilder(
            session,
            retrieval_service=retrieval,  # type: ignore[arg-type]
            budget=ContextBudget(
                recent_message_count=2,
                session_characters=40,
                retrieval_characters=100,
                intelligence_characters=100,
            ),
        ).build(
            learning_session=learning_session,
            question="How do I compare fractions?",
        )

    assert context.question == "How do I compare fractions?"
    assert [message.content for message in context.session_messages] == ["older turn 3", "older turn 4"]
    assert context.focus == CurrentFocus(concept_key="fractions")
    assert context.debug.retrieval_source_refs == ("book#page=12",)
    assert context.debug.session_message_ids == tuple(message.message_id for message in context.session_messages)
    assert retrieval.calls == [
        {
            "student_id": student.id,
            "question": "How do I compare fractions?",
            "grade_level": 5,
            "subject": "MATH",
            "focus": CurrentFocus(concept_key="fractions"),
            "character_budget": 100,
        }
    ]
    assert context.character_count <= len(context.question) + 40 + 100 + 100


def test_relevant_current_state_outranks_history_and_excludes_inactive_or_other_subject_intelligence(
    factory: sessionmaker[Session],
) -> None:
    with factory.begin() as session:
        student, learning_session, run = _seed(session)
        active_state = CurrentLearningState(
            student_id=student.id,
            processing_run_id=run.id,
            subject="MATH",
            state_type="active_difficulty",
            concept_ref="fractions",
            detail="Needs a small check when comparing fractions.",
            status="ACTIVE",
            evidence_refs=[],
            policy_version=CURRENT_STATE_POLICY_VERSION,
        )
        inactive_state = CurrentLearningState(
            student_id=student.id,
            processing_run_id=run.id,
            subject="MATH",
            state_type="active_difficulty",
            concept_ref="fractions",
            detail="Resolved fractions note.",
            status="RESOLVED",
            evidence_refs=[],
        )
        stable_math = LearnerPattern(
            student_id=student.id,
            processing_run_id=run.id,
            pattern_type="support_need",
            pattern_key="support_need:fractions",
            scope={"subject": "MATH", "concept_ref": "fractions"},
            status="STABLE",
            support_count=3,
            counter_count=0,
            detail="Historical fractions support note.",
        )
        science = LearnerPattern(
            student_id=student.id,
            processing_run_id=run.id,
            pattern_type="support_need",
            pattern_key="support_need:plants",
            scope={"subject": "SCIENCE", "concept_ref": "plants"},
            status="STABLE",
            support_count=3,
            counter_count=0,
            detail="Science plants note.",
        )
        unrelated_math = LearnerPattern(
            student_id=student.id,
            processing_run_id=run.id,
            pattern_type="support_need",
            pattern_key="support_need:decimals",
            scope={"subject": "MATH", "concept_ref": "decimals"},
            status="STABLE",
            support_count=3,
            counter_count=0,
            detail="Math decimals note.",
        )
        resolved = LearnerPattern(
            student_id=student.id,
            processing_run_id=run.id,
            pattern_type="support_need",
            pattern_key="support_need:fractions:resolved",
            scope={"subject": "MATH", "concept_ref": "fractions", "phase": "old"},
            status="RESOLVED",
            support_count=3,
            counter_count=3,
            detail="Resolved historical fractions note.",
        )
        session.add_all([active_state, inactive_state, stable_math, science, unrelated_math, resolved])
        session.flush()
        selection = select_relevant_intelligence(
            session,
            student_id=student.id,
            subject="MATH",
            question="I solved a fractions problem independently. Can I check it?",
            focus=CurrentFocus(concept_key="fractions"),
        )

    assert [item.source_kind for item in selection] == ["current_state", "stable_pattern"]
    assert [item.source_id for item in selection] == [active_state.id, stable_math.id]
    assert inactive_state.id not in {item.source_id for item in selection}
    assert science.id not in {item.source_id for item in selection}
    assert unrelated_math.id not in {item.source_id for item in selection}
    assert resolved.id not in {item.source_id for item in selection}


def test_current_question_is_authoritative_over_relevant_stable_history(
    factory: sessionmaker[Session],
) -> None:
    retrieval = RecordingRetrieval()
    with factory.begin() as session:
        student, learning_session, run = _seed(session)
        session.add(
            LearnerPattern(
                student_id=student.id,
                processing_run_id=run.id,
                pattern_type="support_need",
                pattern_key="support_need:fractions",
                scope={"subject": "MATH", "concept_ref": "fractions"},
                status="STABLE",
                support_count=3,
                counter_count=0,
                detail="Older history says fractions sometimes needed support.",
            )
        )
        context = TutorContextBuilder(
            session, retrieval_service=retrieval  # type: ignore[arg-type]
        ).build(
            learning_session=learning_session,
            question="I solved fractions independently today. Please check my reasoning.",
            focus=CurrentFocus(concept_key="fractions"),
        )

    assert context.question == "I solved fractions independently today. Please check my reasoning."
    assert context.intelligence[0].source_kind == "stable_pattern"
    assert context.debug.intelligence_source_kinds == ("stable_pattern",)
