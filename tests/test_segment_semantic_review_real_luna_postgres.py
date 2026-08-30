"""Opt-in, synthetic real-model verification for the Segment semantic reviewer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.segment_reviews import review_completed_segment
from services.model_gateway.factory import create_segment_evidence_gateway, create_tutor_gateway
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import AIExecution, LearningMessage, LearningSegment, LearningSession, ModelTask, Student, User
from services.tutor.runtime import build_tutor_model_payload


pytestmark = [
    pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL is required"),
    pytest.mark.skipif(
        os.getenv("RUN_REAL_LUNA_SEGMENT_REVIEW") != "1",
        reason="Set RUN_REAL_LUNA_SEGMENT_REVIEW=1 for controlled real-model verification.",
    ),
]


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE ai_executions, jobs, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _segment(session: Session, *, subject: str = "MATH") -> tuple[LearningSession, LearningSegment]:
    user = User(identity_provider="real-luna-fixture", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Synthetic Review Student")
    session.add(student)
    session.flush()
    closed_at = datetime(2026, 8, 29, 12, tzinfo=UTC)
    learning_session = LearningSession(student_id=student.id, subject=subject, status="CLOSED", closed_at=closed_at)
    session.add(learning_session)
    session.flush()
    segment = LearningSegment(session_id=learning_session.id, sequence=1, closed_at=closed_at, closure_reason="SESSION_CLOSED")
    session.add(segment)
    session.flush()
    return learning_session, segment


def _messages(
    session: Session,
    *,
    learning_session: LearningSession,
    segment: LearningSegment,
    messages: list[tuple[str, str, dict[str, object] | None]],
) -> None:
    start = datetime(2026, 8, 29, 11, tzinfo=UTC)
    for index, (role, content, payload) in enumerate(messages):
        session.add(
            LearningMessage(
                session_id=learning_session.id,
                segment_id=segment.id,
                role=role,
                content=content,
                payload=payload or {},
                created_at=start + timedelta(seconds=index),
            )
        )
    session.flush()


def test_real_luna_segment_reviewer_representative_cases(factory: sessionmaker[Session]) -> None:
    """Exercise strict structured Segment Review via the configured real route only."""

    cases = [
        (
            "casual_no_learning",
            "MATH",
            [("student", "Hello Lina! How are you today?", None), ("tutor", "Hello! I am glad you are here.", None)],
            lambda output: output["findings"] == [],
        ),
        (
            "learning_without_candidate",
            "MATH",
            [
                ("tutor", "Why are one half and two fourths equal?", None),
                ("student", "Because two fourths covers the same amount as one half when the whole is split evenly.", None),
            ],
            lambda output: len(output["findings"]) >= 1,
        ),
        (
            "bare_wrong_answer",
            "MATH",
            [("tutor", "Which is larger, one half or one fourth?", None), ("student", "One fourth.", None)],
            lambda output: all(finding["validated_event_type"] != "misconception_signal" for finding in output["findings"]),
        ),
        (
            "explicit_misconception_then_correction",
            "MATH",
            [
                ("tutor", "Which is larger, one half or one fourth? Explain why.", None),
                ("student", "One fourth is bigger than one half because 4 is bigger than 2.", None),
                ("tutor", "Think about how large each equal piece is when the denominator is larger.", None),
                ("student", "Oh, I see. One half is bigger because each half is a larger piece than each fourth.", None),
            ],
            lambda output: any(
                finding["validated_event_type"] == "misconception_signal"
                and finding["misconception_evidence"] is not None
                for finding in output["findings"]
            ) and any(
                finding["validated_event_type"] == "self_correction"
                and finding["dimensions"]["self_correction"] in {"prompted", "self_initiated"}
                for finding in output["findings"]
            ),
        ),
        (
            "teaching_method_outcome",
            "MATH",
            [
                (
                    "tutor",
                    "Use these fraction circles to compare the pieces.",
                    {"teaching_method_id": "CONCRETE_EXAMPLE", "teaching_method_registry_version": "teaching-method-registry-v1"},
                ),
                ("student", "Using the fraction circles helped me see that one half is larger than one fourth.", None),
            ],
            lambda output: any(
                finding["validated_event_type"] == "strategy_outcome"
                and finding["teaching_method_id"] == "CONCRETE_EXAMPLE"
                and finding["dimensions"]["strategy_effectiveness"] != "not_evaluable"
                for finding in output["findings"]
            ),
        ),
        (
            "cross_subject_inside_math",
            "MATH",
            [
                ("tutor", "What causes the moon phases?", None),
                ("student", "They change because the Sun lights different parts of the Moon as it moves around Earth.", None),
            ],
            lambda output: output["segment_kind"] == "LEARNING"
            and output["primary_broad_subject"] == "SCIENCE"
            and len(output["findings"]) >= 1,
        ),
    ]

    outcomes: dict[str, dict[str, object]] = {}
    with factory.begin() as session:
        for name, subject, messages, accepted in cases:
            learning_session, segment = _segment(session, subject=subject)
            _messages(session, learning_session=learning_session, segment=segment, messages=messages)
            outcome = review_completed_segment(
                session,
                learning_session=learning_session,
                segment=segment,
                gateway=create_segment_evidence_gateway(session),
            )
            output = outcome.review.output
            assert isinstance(output, dict), name
            assert accepted(output), name
            outcomes[name] = output

    assert set(outcomes) == {case[0] for case in cases}


def test_real_luna_primary_tutor_call_keeps_provisional_subject_optional_and_single(
    factory: sessionmaker[Session],
) -> None:
    """The v8 hint stays inside the one existing Tutor execution."""

    with factory.begin() as session:
        result = create_tutor_gateway(session).execute(
            ModelTask.TUTOR,
            build_tutor_model_payload(
                question="Why do plants need sunlight to make food?"
            ),
        )
        executions = list(session.query(AIExecution).filter_by(task="tutor").all())

        assert result.output.get("provisional_broad_subject") in {
            None,
            "MATH",
            "SCIENCE",
            "LANGUAGE_ARTS",
            "SOCIAL_STUDIES",
            "COMPUTING",
            "RELIGIOUS_STUDIES",
            "ARTS",
            "PHYSICAL_EDUCATION",
            "GENERAL_KNOWLEDGE",
            "OTHER",
        }
        assert len(executions) == 1
        assert executions[0].provider == "openai"
        assert executions[0].model == "gpt-5.6-luna"
        assert executions[0].success is True
