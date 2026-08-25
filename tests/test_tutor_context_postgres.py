"""PostgreSQL contracts for TASK-017 Tutor context assembly."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.current_state import CURRENT_STATE_POLICY_VERSION
from services.intelligence.patterns import PATTERN_POLICY_VERSION
from services.intelligence.selection import select_relevant_intelligence
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CurrentLearningState,
    IntelligenceProcessingRun,
    LearnerPattern,
    LearningMessage,
    LearningSession,
    ModelTask,
    Student,
    User,
)
from services.platform.safety import SafetyAction, SafetyDecision
from services.retrieval.service import CurrentFocus, RetrievedBlock
from services.tutor.context import ContextBudget, TutorContextBuilder
from services.tutor.runtime import TutorRuntime, build_tutor_model_payload


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


class RecordingTutorProvider:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route
        self.payloads.append(payload)
        yield StreamComplete(
            ModelResult(
                output={
                    "text": "Let's keep working through it together.",
                    "suggested_actions": [],
                    "teaching_mode": None,
                    "teaching_strategy": None,
                    "teaching_method_id": None,
                    "prior_method_relation": None,
                    "candidate_metadata": None,
                }
            )
        )


class AllowSafetyPolicy:
    def evaluate(self, **_: object) -> SafetyDecision:
        return SafetyDecision(SafetyAction.ALLOW, None, "BASELINE", 1, "TEST_ALLOW", "normal", None)


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


def test_recent_context_keeps_immediate_tutor_question_ahead_of_older_long_message(
    factory: sessionmaker[Session],
) -> None:
    """CTX-01: an opaque answer needs its immediately preceding Tutor question."""

    retrieval = RecordingRetrieval()
    tutor_question = (
        "Question 1: 6 stickers are shared equally between 2 children. "
        "How many stickers does each child get? A) 2 B) 3 C) 4"
    )
    with factory.begin() as session:
        _, learning_session, _ = _seed(session)
        base = datetime.now(UTC)
        older_long_tutor_message = "Older explanation: " + ("x" * 530)
        messages = [
            LearningMessage(
                session_id=learning_session.id,
                role="tutor",
                content=older_long_tutor_message,
                created_at=base,
            ),
            LearningMessage(
                session_id=learning_session.id,
                role="student",
                content="make me a quiz",
                created_at=base + timedelta(seconds=1),
            ),
            LearningMessage(
                session_id=learning_session.id,
                role="tutor",
                content=tutor_question,
                created_at=base + timedelta(seconds=2),
            ),
            LearningMessage(
                session_id=learning_session.id,
                role="student",
                content="B) 3",
                created_at=base + timedelta(seconds=3),
            ),
        ]
        session.add_all(messages)
        session.flush()
        context = TutorContextBuilder(
            session,
            retrieval_service=retrieval,  # type: ignore[arg-type]
            budget=ContextBudget(
                recent_message_count=4,
                session_characters=600,
                retrieval_characters=100,
                intelligence_characters=100,
            ),
        ).build(learning_session=learning_session, question="B) 3")

    assert [message.content for message in context.immediate_bridge] == [tutor_question]
    assert messages[2].id in context.debug.immediate_bridge_message_ids
    assert messages[3].id not in context.debug.session_message_ids
    assert sum(len(message.content) for message in context.session_messages) <= 600


def test_model_input_keeps_immediate_tutor_question_for_opaque_answer(
    factory: sessionmaker[Session],
) -> None:
    """CTX-01 reaches the one-call Tutor input, not merely a private helper."""

    retrieval = RecordingRetrieval()
    tutor_question = (
        "Question 1: 6 stickers are shared equally between 2 children. "
        "How many stickers does each child get? A) 2 B) 3 C) 4"
    )
    with factory.begin() as session:
        _, learning_session, _ = _seed(session)
        base = datetime.now(UTC)
        session.add_all(
            [
                LearningMessage(
                    session_id=learning_session.id,
                    role="tutor",
                    content="Older explanation: " + ("x" * 530),
                    created_at=base,
                ),
                LearningMessage(
                    session_id=learning_session.id,
                    role="student",
                    content="make me a quiz",
                    created_at=base + timedelta(seconds=1),
                ),
                LearningMessage(
                    session_id=learning_session.id,
                    role="tutor",
                    content=tutor_question,
                    created_at=base + timedelta(seconds=2),
                ),
                LearningMessage(
                    session_id=learning_session.id,
                    role="student",
                    content="B) 3",
                    created_at=base + timedelta(seconds=3),
                ),
            ]
        )
        session.flush()
        context = TutorContextBuilder(
            session,
            retrieval_service=retrieval,  # type: ignore[arg-type]
            budget=ContextBudget(
                recent_message_count=4,
                session_characters=600,
                retrieval_characters=100,
                intelligence_characters=100,
            ),
        ).build(learning_session=learning_session, question="B) 3")
        payload = build_tutor_model_payload(
            question=context.question,
            immediate_bridge=[
                {"role": message.role, "content": message.content}
                for message in context.immediate_bridge
            ],
            session_messages=[
                {"role": message.role, "content": message.content}
                for message in context.session_messages
            ],
        )

    assert "Current Turn:\nStudent question:\nB) 3" in str(payload["input"])
    assert tutor_question in str(payload["input"])


def test_ctx02_runtime_keeps_oversized_immediate_tutor_turn_in_one_call_input(
    factory: sessionmaker[Session],
) -> None:
    """CTX-02: a short opaque follow-up keeps its immediate Tutor activity bridge."""

    retrieval = RecordingRetrieval()
    provider = RecordingTutorProvider()
    immediate_tutor_turn = "Flashlight and ball activity: " + ("look at the ball, not the light. " * 45)
    follow_up = "ما زبطت معي الصو في عيوني"
    with factory.begin() as session:
        _, learning_session, _ = _seed(session)
        base = datetime.now(UTC)
        older_recent_turn = "Older current-session continuity: we were comparing shadows."
        older_too_large_turn = "Older bounded history: " + ("x" * 580)
        older_recent_message = LearningMessage(
            session_id=learning_session.id,
            role="tutor",
            content=older_recent_turn,
            created_at=base - timedelta(seconds=2),
        )
        bridge_message = LearningMessage(
            session_id=learning_session.id,
            role="tutor",
            content=immediate_tutor_turn,
            created_at=base - timedelta(seconds=1),
        )
        session.add_all(
            [
                LearningMessage(
                    session_id=learning_session.id,
                    role="student",
                    content=older_too_large_turn,
                    created_at=base - timedelta(seconds=3),
                ),
                older_recent_message,
                bridge_message,
            ]
        )
        session.flush()
        runtime = TutorRuntime(
            session,
            context_builder=TutorContextBuilder(
                session,
                retrieval_service=retrieval,  # type: ignore[arg-type]
                budget=ContextBudget(
                    recent_message_count=4,
                    session_characters=600,
                    immediate_bridge_characters=1200,
                    retrieval_characters=100,
                    intelligence_characters=100,
                ),
            ),
            safety_policy=AllowSafetyPolicy(),  # type: ignore[arg-type]
            gateway=ModelGateway(
                session,
                routes={ModelTask.TUTOR: ModelRoute("fixture", "ctx02")},
                providers={"fixture": provider},
            ),
        )

        list(runtime.stream_turn(learning_session=learning_session, question=follow_up))

        current_student_message = session.query(LearningMessage).filter_by(
            session_id=learning_session.id,
            role="student",
            content=follow_up,
        ).one()
        persisted_tutor_message = session.query(LearningMessage).filter_by(
            session_id=learning_session.id,
            role="tutor",
        ).order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc()).first()
        assert persisted_tutor_message is not None
        model_input = str(provider.payloads[0]["input"])

    assert current_student_message.content == follow_up
    assert f"Current Turn:\nStudent question:\n{follow_up}" in model_input
    assert immediate_tutor_turn[:1200] in model_input
    assert immediate_tutor_turn not in model_input
    assert model_input.count(follow_up) == 1
    assert older_recent_turn in model_input
    assert older_too_large_turn not in model_input
    assert model_input.index("Current Turn:") < model_input.index("Immediate bridge:")
    assert model_input.index("Immediate bridge:") < model_input.index("Bounded older current-session continuity:")
    assert model_input.index("Bounded older current-session continuity:") < model_input.index("Retrieved curriculum:")
    assert persisted_tutor_message.payload["context_debug"] == {
        "current_turn_message_id": str(current_student_message.id),
        "immediate_bridge_message_ids": [str(bridge_message.id)],
        "older_continuity_message_ids": [str(older_recent_message.id)],
        "session_message_ids": [str(older_recent_message.id)],
        "retrieval_source_refs": ["book#page=12"],
        "intelligence_source_ids": [],
    }


def test_recent_persisted_topic_metadata_supports_an_ambiguous_continuation(
    factory: sessionmaker[Session],
) -> None:
    retrieval = RecordingRetrieval()
    with factory.begin() as session:
        _, learning_session, _ = _seed(session)
        session.add(
            LearningMessage(
                session_id=learning_session.id,
                role="tutor",
                content="Equivalent fractions name the same amount.",
                payload={"concept_ref": "equivalent_fractions"},
            )
        )
        context = TutorContextBuilder(
            session,
            retrieval_service=retrieval,  # type: ignore[arg-type]
        ).build(
            learning_session=learning_session,
            question="Continue.",
        )

    assert context.focus == CurrentFocus(concept_key="equivalent_fractions")
    assert retrieval.calls[0]["focus"] == CurrentFocus(concept_key="equivalent_fractions")


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
            policy_version=PATTERN_POLICY_VERSION,
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
            policy_version=PATTERN_POLICY_VERSION,
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
            policy_version=PATTERN_POLICY_VERSION,
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
            policy_version=PATTERN_POLICY_VERSION,
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
                policy_version=PATTERN_POLICY_VERSION,
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
