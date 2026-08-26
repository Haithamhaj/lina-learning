"""Selection contracts for CTX-03C complete current-Segment exchanges."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.db.models import AIExecution, LearningMessage, LearningSegment, LearningSession, ModelTask, Student, User
from services.retrieval.service import RetrievedBlock, RetrievalService
from services.tutor.context import TutorContextBuilder
from services.tutor.exchanges import complete_exchanges_for_segment, serialize_exchange


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for CTX-03C exchange tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE learning_exchange_embeddings, learning_messages, learning_segments, ai_executions, "
                "learning_sessions, students, users CASCADE"
            )
        )
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _session_and_segment(session: Session) -> tuple[LearningSession, LearningSegment]:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id)
    session.add(student)
    session.flush()
    learning_session = LearningSession(student_id=student.id, subject="MATH")
    session.add(learning_session)
    session.flush()
    segment = LearningSegment(session_id=learning_session.id, sequence=1)
    session.add(segment)
    session.flush()
    return learning_session, segment


def _student(session: Session, learning_session: LearningSession, segment: LearningSegment, content: str, created_at: datetime) -> LearningMessage:
    message = LearningMessage(session_id=learning_session.id, segment_id=segment.id, role="student", content=content, created_at=created_at)
    session.add(message)
    session.flush()
    return message


def _tutor_for(session: Session, learning_session: LearningSession, segment: LearningSegment, student: LearningMessage, content: str, created_at: datetime) -> LearningMessage:
    execution = AIExecution(task="tutor", provider="fixture", model="fixture", latency_ms=1, success=True, source_message_id=student.id, learning_session_id=learning_session.id)
    session.add(execution)
    session.flush()
    message = LearningMessage(session_id=learning_session.id, segment_id=segment.id, role="tutor", content=content, ai_execution_id=execution.id, created_at=created_at)
    session.add(message)
    session.flush()
    return message


def test_complete_exchange_selection_never_pairs_later_tutor_to_failed_student(
    factory: sessionmaker[Session],
) -> None:
    """Catches chronological pairing that turns failed Student A into Tutor B's source."""

    with factory.begin() as session:
        learning_session, segment = _session_and_segment(session)
        base = datetime(2026, 8, 26, tzinfo=UTC)
        _student(session, learning_session, segment, "Student A failed", base)
        student_b = _student(session, learning_session, segment, "Student B succeeded", base + timedelta(seconds=1))
        _tutor_for(session, learning_session, segment, student_b, "Tutor B", base + timedelta(seconds=2))

        exchanges = complete_exchanges_for_segment(
            session,
            learning_session=learning_session,
            segment=segment,
        )

    assert [(exchange.student_content, exchange.tutor_content) for exchange in exchanges] == [
        ("Student B succeeded", "Tutor B")
    ]
    assert serialize_exchange(exchanges[0]) == "Student:\nStudent B succeeded\n\nTutor:\nTutor B"


def test_context_uses_disjoint_complete_exchange_groups_from_latest_segment(
    factory: sessionmaker[Session],
) -> None:
    """Catches reintroduction of individual session-message windows or duplicate exchanges."""

    class Retrieval:
        def retrieve(self, **_: object) -> list[RetrievedBlock]:
            return []

    with factory.begin() as session:
        learning_session, segment = _session_and_segment(session)
        base = datetime(2026, 8, 26, tzinfo=UTC)
        first = _student(session, learning_session, segment, "first", base)
        _tutor_for(session, learning_session, segment, first, "first reply", base + timedelta(seconds=1))
        second = _student(session, learning_session, segment, "second", base + timedelta(seconds=2))
        _tutor_for(session, learning_session, segment, second, "second reply", base + timedelta(seconds=3))
        third = _student(session, learning_session, segment, "third", base + timedelta(seconds=4))
        _tutor_for(session, learning_session, segment, third, "third reply", base + timedelta(seconds=5))
        current = _student(session, learning_session, segment, "current", base + timedelta(seconds=6))

        context = TutorContextBuilder(session, retrieval_service=Retrieval()).build(
            learning_session=learning_session,
            question="current",
            current_turn_message_id=current.id,
        )

    assert context.immediate_exchange is not None
    assert context.immediate_exchange.student_content == "third"
    assert [exchange.student_content for exchange in context.recent_exchanges] == ["second"]
    all_ids = [
        *context.immediate_exchange.message_ids,
        *(message_id for exchange in context.recent_exchanges for message_id in exchange.message_ids),
        *(message_id for exchange in context.semantic_recall_exchanges for message_id in exchange.message_ids),
    ]
    assert len(all_ids) == len(set(all_ids))


def test_context_batches_current_question_with_missing_older_exchange_embedding_once(
    factory: sessionmaker[Session],
) -> None:
    """Catches separate current-question embedding calls for recall and curriculum retrieval."""

    class CountingProvider:
        def __init__(self) -> None:
            self.inputs: list[list[str]] = []

        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            inputs = payload["input"]
            assert isinstance(inputs, list)
            self.inputs.append(inputs)
            return ModelResult(output={"embeddings": [[1.0] + [0.0] * 1535 for _ in inputs]})

    with factory.begin() as session:
        learning_session, segment = _session_and_segment(session)
        base = datetime(2026, 8, 26, tzinfo=UTC)
        for index in range(3):
            student = _student(session, learning_session, segment, f"Student {index}", base + timedelta(seconds=index * 2))
            _tutor_for(session, learning_session, segment, student, f"Tutor {index}", base + timedelta(seconds=index * 2 + 1))
        current = _student(session, learning_session, segment, "Current", base + timedelta(seconds=7))
        provider = CountingProvider()
        gateway = ModelGateway(
            session,
            routes={ModelTask.EMBEDDING: ModelRoute("fixture", "text-embedding-3-small")},
            providers={"fixture": provider},
        )
        context = TutorContextBuilder(
            session,
            retrieval_service=RetrievalService(session, embedding_gateway=gateway),
        ).build(learning_session=learning_session, question="Current", current_turn_message_id=current.id)

    assert len(provider.inputs) == 1
    assert provider.inputs[0] == ["Current", "Student:\nStudent 0\n\nTutor:\nTutor 0"]
    assert [exchange.student_content for exchange in context.semantic_recall_exchanges] == ["Student 0"]
