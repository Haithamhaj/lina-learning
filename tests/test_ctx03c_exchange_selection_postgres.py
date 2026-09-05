"""Selection contracts for CTX-03C complete current-Segment exchanges."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.db.models import AIExecution, LearningExchangeEmbedding, LearningMessage, LearningSegment, LearningSession, ModelTask, Student, User
from services.retrieval.service import RetrievedBlock, RetrievalService
from services.tutor.context import ContextBudget, TutorContextBuilder
from services.tutor.exchanges import (
    complete_exchanges_for_segment,
    immediate_exchange_for_current_turn,
    persist_exchange_embedding,
    serialize_exchange,
)


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


def test_immediate_exchange_uses_the_latest_session_pair_even_when_safety_has_no_segment(
    factory: sessionmaker[Session],
) -> None:
    """Catches CTX-03C deriving CTX-02 Immediate Exchange from Segment lineage."""

    class Retrieval:
        def retrieve(self, **_: object) -> list[RetrievedBlock]:
            return []

    with factory.begin() as session:
        learning_session, segment = _session_and_segment(session)
        base = datetime(2026, 8, 26, tzinfo=UTC)
        normal_student = _student(session, learning_session, segment, "normal Segment Student", base)
        _tutor_for(session, learning_session, segment, normal_student, "normal Segment Tutor", base + timedelta(seconds=1))
        safety_student = LearningMessage(
            session_id=learning_session.id,
            role="student",
            content="I am in immediate danger",
            created_at=base + timedelta(seconds=2),
        )
        safety_tutor = LearningMessage(
            session_id=learning_session.id,
            role="tutor",
            content="Move away and get a trusted grown-up now.",
            created_at=base + timedelta(seconds=3),
        )
        current = LearningMessage(
            session_id=learning_session.id,
            role="student",
            content="I am safe now",
            created_at=base + timedelta(seconds=4),
        )
        session.add_all([safety_student, safety_tutor, current])
        session.flush()

        context = TutorContextBuilder(session, retrieval_service=Retrieval()).build(
            learning_session=learning_session,
            question=current.content,
            current_turn_message_id=current.id,
        )

    assert context.immediate_exchange is not None
    assert context.immediate_exchange.message_ids == (safety_student.id, safety_tutor.id)
    assert context.immediate_exchange.student_content == safety_student.content
    assert context.immediate_exchange.tutor_content == safety_tutor.content
    assert normal_student.id not in context.debug.immediate_exchange_message_ids


def test_immediate_exchange_preserves_tutor_only_session_history(
    factory: sessionmaker[Session],
) -> None:
    """Catches a CTX-03C assumption that every visible Tutor reply has a Student pair."""

    class Retrieval:
        def retrieve(self, **_: object) -> list[RetrievedBlock]:
            return []

    with factory.begin() as session:
        learning_session, _ = _session_and_segment(session)
        base = datetime(2026, 8, 26, tzinfo=UTC)
        tutor = LearningMessage(session_id=learning_session.id, role="tutor", content="Tutor-only safety response", created_at=base)
        current = LearningMessage(session_id=learning_session.id, role="student", content="next", created_at=base + timedelta(seconds=1))
        session.add_all([tutor, current])
        session.flush()
        context = TutorContextBuilder(session, retrieval_service=Retrieval()).build(
            learning_session=learning_session,
            question=current.content,
            current_turn_message_id=current.id,
        )

    assert context.immediate_exchange is not None
    assert context.immediate_exchange.message_ids == (tutor.id,)
    assert context.immediate_exchange.student_content is None
    assert context.immediate_exchange.tutor_content == tutor.content


def test_canvas_tutor_continuity_never_pairs_it_with_an_earlier_chat_student(
    factory: sessionmaker[Session],
) -> None:
    """Chat A stays an exact pair while Chat C sees Canvas B as Tutor-only continuity."""

    with factory.begin() as session:
        learning_session, segment = _session_and_segment(session)
        base = datetime(2026, 9, 5, tzinfo=UTC)
        chat_a = _student(session, learning_session, segment, "Chat Student A", base)
        tutor_a = _tutor_for(session, learning_session, segment, chat_a, "Chat Tutor A", base + timedelta(seconds=1))
        canvas_execution = AIExecution(
            task=ModelTask.TUTOR.value,
            provider="fixture",
            model="fixture",
            latency_ms=1,
            success=True,
            operation_type="studio_interaction_tutor_turn",
            learning_session_id=learning_session.id,
            source_message_id=None,
        )
        session.add(canvas_execution)
        session.flush()
        canvas_b = LearningMessage(
            session_id=learning_session.id,
            role="tutor",
            content="Canvas Tutor B",
            ai_execution_id=canvas_execution.id,
            payload={"turn_origin": "STUDIO_INTERACTION", "student_interaction_id": str(uuid4())},
            created_at=base + timedelta(seconds=2),
        )
        chat_c = _student(session, learning_session, segment, "Chat Student C", base + timedelta(seconds=3))
        session.add_all([canvas_b, chat_c])
        session.flush()

        immediate = immediate_exchange_for_current_turn(
            session,
            learning_session=learning_session,
            current_turn=chat_c,
        )
        exchanges = complete_exchanges_for_segment(session, learning_session=learning_session, segment=segment)

    assert immediate is not None
    assert immediate.tutor_message_id == canvas_b.id
    assert immediate.student_message_id is None
    assert immediate.student_content is None
    assert immediate.tutor_content == "Canvas Tutor B"
    assert [(item.student_message_id, item.tutor_message_id) for item in exchanges] == [(chat_a.id, tutor_a.id)]


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


def test_existing_oldest_vector_remains_eligible_beyond_missing_embedding_batch_limit(
    factory: sessionmaker[Session],
) -> None:
    """Catches semantic recall treating the lazy-indexing batch as its candidate pool."""

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            values = payload["input"]
            assert isinstance(values, list)
            return ModelResult(
                output={"embeddings": [[1.0] + [0.0] * 1535, *([[0.0, 1.0] + [0.0] * 1534] * (len(values) - 1))]}
            )

    with factory.begin() as session:
        learning_session, segment = _session_and_segment(session)
        base = datetime(2026, 8, 26, tzinfo=UTC)
        pairs: list[tuple[LearningMessage, LearningMessage]] = []
        for index in range(11):
            student = _student(session, learning_session, segment, f"Student {index}", base + timedelta(seconds=index * 2))
            tutor = _tutor_for(session, learning_session, segment, student, f"Tutor {index}", base + timedelta(seconds=index * 2 + 1))
            pairs.append((student, tutor))
        persist_exchange_embedding(
            session,
            student_message=pairs[0][0],
            tutor_message=pairs[0][1],
            embedding=[1.0] + [0.0] * 1535,
            embedding_model="text-embedding-3-small",
        )
        current = _student(session, learning_session, segment, "Current", base + timedelta(seconds=23))
        gateway = ModelGateway(
            session,
            routes={ModelTask.EMBEDDING: ModelRoute("fixture", "text-embedding-3-small")},
            providers={"fixture": Provider()},
        )
        context = TutorContextBuilder(
            session,
            retrieval_service=RetrievalService(session, embedding_gateway=gateway),
        ).build(learning_session=learning_session, question="Current", current_turn_message_id=current.id)

    assert [exchange.student_content for exchange in context.semantic_recall_exchanges] == ["Student 0"]


def test_semantic_priority_lineage_keeps_state_pin_ahead_of_chronological_presentation(
    factory: sessionmaker[Session],
) -> None:
    """Catches CTX-03D receiving Luna display order instead of CTX-03C's State-first priority."""

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            inputs = payload["input"]
            assert isinstance(inputs, list) and inputs == ["Current"]
            return ModelResult(output={"embeddings": [[1.0] + [0.0] * 1535]})

    with factory.begin() as session:
        learning_session, segment = _session_and_segment(session)
        base = datetime(2026, 8, 26, tzinfo=UTC)
        pinned_student = _student(session, learning_session, segment, "State-pinned older", base)
        pinned_tutor = _tutor_for(session, learning_session, segment, pinned_student, "Pinned reply", base + timedelta(seconds=1))
        ordinary_student = _student(session, learning_session, segment, "Ordinary newer", base + timedelta(seconds=2))
        ordinary_tutor = _tutor_for(session, learning_session, segment, ordinary_student, "Ordinary reply", base + timedelta(seconds=3))
        recent_student = _student(session, learning_session, segment, "Recent", base + timedelta(seconds=4))
        _tutor_for(session, learning_session, segment, recent_student, "Recent reply", base + timedelta(seconds=5))
        immediate_student = _student(session, learning_session, segment, "Immediate", base + timedelta(seconds=6))
        _tutor_for(session, learning_session, segment, immediate_student, "Immediate reply", base + timedelta(seconds=7))
        current = _student(session, learning_session, segment, "Current", base + timedelta(seconds=8))
        segment.structured_state = {
            "schema_version": "structured-segment-state-v1",
            "active_goal": "Keep the State-pinned exchange available.",
            "unresolved_point": None,
            "active_references": [],
            "established_facts": [],
            "source_message_ids": [str(pinned_student.id)],
        }
        persist_exchange_embedding(
            session,
            student_message=pinned_student,
            tutor_message=pinned_tutor,
            embedding=[0.0, 1.0] + [0.0] * 1534,
            embedding_model="text-embedding-3-small",
        )
        persist_exchange_embedding(
            session,
            student_message=ordinary_student,
            tutor_message=ordinary_tutor,
            embedding=[1.0] + [0.0] * 1535,
            embedding_model="text-embedding-3-small",
        )
        gateway = ModelGateway(
            session,
            routes={ModelTask.EMBEDDING: ModelRoute("fixture", "text-embedding-3-small")},
            providers={"fixture": Provider()},
        )
        context = TutorContextBuilder(
            session,
            retrieval_service=RetrievalService(session, embedding_gateway=gateway),
        ).build(learning_session=learning_session, question="Current", current_turn_message_id=current.id)

    assert [exchange.student_content for exchange in context.semantic_recall_exchanges] == [
        "State-pinned older",
        "Ordinary newer",
    ]
    assert context.semantic_recall_priority_message_ids == (
        (pinned_student.id, pinned_tutor.id),
        (ordinary_student.id, ordinary_tutor.id),
    )


def test_zero_similarity_does_not_force_an_older_exchange_into_semantic_recall(
    factory: sessionmaker[Session],
) -> None:
    """The recall cutoff is a calibration boundary, not a nearest-neighbour fallback."""

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route, payload
            return ModelResult(output={"embeddings": [[1.0] + [0.0] * 1535]})

    with factory.begin() as session:
        learning_session, segment = _session_and_segment(session)
        base = datetime(2026, 8, 26, tzinfo=UTC)
        oldest = _student(session, learning_session, segment, "irrelevant older exchange", base)
        oldest_tutor = _tutor_for(session, learning_session, segment, oldest, "irrelevant reply", base + timedelta(seconds=1))
        middle = _student(session, learning_session, segment, "recent exchange", base + timedelta(seconds=2))
        _tutor_for(session, learning_session, segment, middle, "recent reply", base + timedelta(seconds=3))
        latest = _student(session, learning_session, segment, "immediate exchange", base + timedelta(seconds=4))
        _tutor_for(session, learning_session, segment, latest, "immediate reply", base + timedelta(seconds=5))
        persist_exchange_embedding(
            session,
            student_message=oldest,
            tutor_message=oldest_tutor,
            embedding=[0.0, 1.0] + [0.0] * 1534,
            embedding_model="text-embedding-3-small",
        )
        current = _student(session, learning_session, segment, "Current", base + timedelta(seconds=6))
        gateway = ModelGateway(
            session,
            routes={ModelTask.EMBEDDING: ModelRoute("fixture", "text-embedding-3-small")},
            providers={"fixture": Provider()},
        )
        context = TutorContextBuilder(
            session,
            retrieval_service=RetrievalService(session, embedding_gateway=gateway),
        ).build(learning_session=learning_session, question="Current", current_turn_message_id=current.id)

    assert context.semantic_recall_exchanges == ()


def test_missing_embedding_backlog_progresses_oldest_first_across_turns(
    factory: sessionmaker[Session],
) -> None:
    """A small per-turn batch must eventually index every older eligible exchange."""

    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            values = payload["input"]
            assert isinstance(values, list)
            return ModelResult(output={"embeddings": [[1.0] + [0.0] * 1535 for _ in values]})

    with factory.begin() as session:
        learning_session, segment = _session_and_segment(session)
        base = datetime(2026, 8, 26, tzinfo=UTC)
        students: list[LearningMessage] = []
        for index in range(4):
            student = _student(session, learning_session, segment, f"Student {index}", base + timedelta(seconds=index * 2))
            _tutor_for(session, learning_session, segment, student, f"Tutor {index}", base + timedelta(seconds=index * 2 + 1))
            students.append(student)
        first_current = _student(session, learning_session, segment, "Current 1", base + timedelta(seconds=8))
        gateway = ModelGateway(
            session,
            routes={ModelTask.EMBEDDING: ModelRoute("fixture", "text-embedding-3-small")},
            providers={"fixture": Provider()},
        )
        builder = TutorContextBuilder(
            session,
            retrieval_service=RetrievalService(session, embedding_gateway=gateway),
            budget=ContextBudget(embedding_batch_limit=1),
        )
        builder.build(learning_session=learning_session, question=first_current.content, current_turn_message_id=first_current.id)
        _tutor_for(session, learning_session, segment, first_current, "Tutor Current 1", base + timedelta(seconds=9))
        second_current = _student(session, learning_session, segment, "Current 2", base + timedelta(seconds=10))
        builder.build(learning_session=learning_session, question=second_current.content, current_turn_message_id=second_current.id)
        stored_ids = set(
            session.scalars(
                select(LearningExchangeEmbedding.student_message_id).where(
                    LearningExchangeEmbedding.session_id == learning_session.id,
                    LearningExchangeEmbedding.segment_id == segment.id,
                )
            )
        )

    assert students[0].id in stored_ids
    assert students[1].id in stored_ids
