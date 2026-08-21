"""PostgreSQL persistence contract for hidden same-call Tutor Candidate Events."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import CandidateEvent, LearningEvidence, LearningEvent, LearningMessage, LearningSession, ModelTask, Student, User
from services.platform.safety import SafetyAction, SafetyDecision
from services.retrieval.service import RetrievedBlock
from services.tutor.context import SessionContextMessage, TutorContext, TutorContextDebug
from services.tutor.runtime import TutorRuntime


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL is required for Candidate Event tests"
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE learning_evidence, learning_events, candidate_events, learning_messages, learning_sessions, students, users, ai_executions CASCADE"))
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


class _ContextBuilder:
    def build(self, *, learning_session: LearningSession, question: str) -> TutorContext:
        message_id = uuid4()
        retrieval = RetrievedBlock(
            text="Equivalent fractions name the same amount.", source_ref="book#page=12", page_number=12,
            block_type="EXERCISE", score=1.0, semantic_key="fractions", semantic_type="EXERCISE",
            concept_key="fractions", source_refs=("book#page=12",), page_numbers=(12,), matched=True,
        )
        return TutorContext(
            question=question, subject=learning_session.subject, grade_level=5, focus=None,
            session_messages=(SessionContextMessage(message_id, "student", question),), retrieval=(retrieval,), intelligence=(),
            debug=TutorContextDebug(None, (message_id,), ("book#page=12",), (), ()),
        )


class _SafetyPolicy:
    def evaluate(self, **_: object) -> SafetyDecision:
        return SafetyDecision(SafetyAction.ALLOW, None, "BASELINE", 1, "TEST_ALLOW", "normal", None)


class _Provider:
    def __init__(self) -> None:
        self.calls = 0

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route
        self.calls += 1
        source_message_id = str(payload["candidate_source_message_id"])
        result = ModelResult(
            output={
                "text": "That is right: one half and two fourths name the same amount.",
                "candidate_metadata": {
                    "version": "candidate-event-v1",
                    "candidates": [{
                        "event_type": "independent_success",
                        "concept_ref": "equivalent_fractions",
                        "summary": "The Student independently identified equivalent fractions.",
                        "signal": "solved_independently",
                        "source_message_ids": [source_message_id],
                        "school_or_extended": "school",
                    }],
                },
            },
            input_tokens=5,
            output_tokens=3,
        )
        yield StreamDelta(str(result.output["text"]))
        yield StreamComplete(result)


def test_same_call_candidate_persists_raw_source_and_never_creates_derived_intelligence(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        user = User(identity_provider="fixture", external_subject=uuid4().hex)
        session.add(user)
        session.flush()
        student = Student(user_id=user.id, display_name="Fixture")
        session.add(student)
        session.flush()
        initial_activity = datetime(2020, 1, 1, tzinfo=UTC)
        learning_session = LearningSession(
            student_id=student.id,
            subject="MATH",
            last_activity_at=initial_activity,
        )
        session.add(learning_session)
        session.flush()
        provider = _Provider()
        gateway = ModelGateway(
            session,
            routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")},
            providers={"fixture": provider},
        )
        runtime = TutorRuntime(
            session,
            context_builder=_ContextBuilder(),
            safety_policy=_SafetyPolicy(),
            gateway=gateway,
        )

        list(runtime.stream_turn(learning_session=learning_session, question="I worked out that one half equals two fourths."))

        candidate = session.query(CandidateEvent).one()
        source = session.get(LearningMessage, candidate.message_id)
        tutor_message = session.query(LearningMessage).filter_by(role="tutor").one()
        assert provider.calls == 1
        assert source is not None and source.role == "student"
        assert candidate.session_id == learning_session.id
        assert candidate.payload["subject"] == "MATH"
        assert candidate.payload["source_message_ids"] == [str(source.id)]
        assert candidate.payload["model_route"] == {"provider": "fixture", "model": "fixture-tutor"}
        assert tutor_message.payload["candidate_metadata_status"] == "persisted"
        assert learning_session.last_activity_at > initial_activity
        assert session.query(LearningEvent).count() == 0
        assert session.query(LearningEvidence).count() == 0
