"""PostgreSQL contract tests for the authenticated Student Math session path."""

from __future__ import annotations

import asyncio
import json
import os
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    AIExecution,
    CandidateEvent,
    ContentDocument,
    ContentIndexRun,
    ContentProcessingRun,
    ContentSemanticProcessingRun,
    LearningMessage,
    LearningSession,
    Student,
    User,
)
from services.platform.db.session import get_session
from services.platform.config import Settings
from services.model_gateway.gateway import ModelGateway, ModelRoute, StreamDelta
from services.platform.db.models import ModelTask
from services.platform.safety import SafetyPolicyService
from services.retrieval.service import RetrievalService
from services.tutor.context import TutorContextBuilder
from services.tutor.candidate_events import SuggestedAction
from services.tutor.runtime import TutorRuntime, TutorTextDelta, TutorTurn
from services.tutor.student_sessions import latest_tutor_suggested_action


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Student session tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE learning_messages, learning_sessions, students, users CASCADE"))
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _student(session: Session, subject: str) -> Student:
    user = User(
        identity_provider="clerk",
        external_subject=subject,
        email=f"{subject}@example.test",
        role="STUDENT",
    )
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name=subject)
    session.add(student)
    session.flush()
    return student


def _ready_grade_five_math_content(session: Session, student: Student) -> None:
    document = ContentDocument(
        student_id=student.id,
        grade_level=5,
        subject="MATH",
        original_storage_key="private/content/math.pdf",
        original_checksum=UUID(int=student.id.int ^ 1).hex * 2,
        filename="math.pdf",
        content_type="application/pdf",
    )
    session.add(document)
    session.flush()
    structural = ContentProcessingRun(
        document_id=document.id,
        kind="STRUCTURAL",
        processor_version="fixture-structural",
        processor_settings_version="fixture",
        status="COMPLETED",
    )
    session.add(structural)
    session.flush()
    semantic = ContentSemanticProcessingRun(
        document_id=document.id,
        structural_processing_run_id=structural.id,
        semantic_schema_version="fixture-schema",
        prompt_version="fixture-prompt",
        model_route_version="fixture:model",
        provider="fixture",
        model="fixture",
        settings_version="fixture",
        status="COMPLETED",
    )
    session.add(semantic)
    session.flush()
    session.add(
        ContentIndexRun(
            document_id=document.id,
            structural_processing_run_id=structural.id,
            semantic_processing_run_id=semantic.id,
            block_schema_version="fixture-blocks",
            embedding_route_version="fixture:embedding",
            embedding_dimensions=1536,
            settings_version="fixture",
            status="COMPLETED",
        )
    )
    session.flush()


def _client(
    postgres_session_factory: sessionmaker[Session],
    *,
    subject: str,
    raise_server_exceptions: bool = True,
) -> TestClient:
    from apps.api.main import app

    def database_session():
        with postgres_session_factory.begin() as session:
            yield session

    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject=subject,
        role=UserRole.STUDENT,
        email=f"{subject}@example.test",
    )
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def _clear_overrides() -> None:
    from apps.api.main import app

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_principal, None)


class _DeltaThenFailureTutorProvider:
    """Simulate a provider that streams text but never reaches a final result."""

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> object:
        del route, payload
        raise AssertionError("The Student Tutor path must use streaming.")

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route, payload
        yield StreamDelta("A partial Tutor response.")
        raise RuntimeError("fixture stream failure")


def _delta_then_failure_runtime(session: Session) -> TutorRuntime:
    return TutorRuntime(
        session,
        context_builder=TutorContextBuilder(session, retrieval_service=RetrievalService(session)),
        safety_policy=SafetyPolicyService(session),
        gateway=ModelGateway(
            session,
            routes={ModelTask.TUTOR: ModelRoute("fixture-stream", "fixture-failure-model")},
            providers={"fixture-stream": _DeltaThenFailureTutorProvider()},
        ),
    )


class _CommittedTurnFixtureRuntime:
    """Persist one final Tutor action so the route transaction boundary is observable."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def stream_turn(self, *, learning_session: LearningSession, question: str, **_: object):
        action = SuggestedAction(label="Give me a hint", kind="NAVIGATION")
        self._session.add(
            LearningMessage(
                session_id=learning_session.id,
                role="tutor",
                content=f"Tutor reply for: {question}",
                payload={"suggested_actions": [action.model_dump()]},
            )
        )
        self._session.flush()
        yield TutorTextDelta("Tutor reply")
        yield TutorTurn("Tutor reply", [action], [], [], None, None, {})


def test_authenticated_student_with_zero_content_starts_and_resumes_one_open_math_session(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")

    client = _client(postgres_session_factory, subject="student-one")
    try:
        first = client.post("/api/v1/student/math/session")
        second = client.post("/api/v1/student/math/session")
    finally:
        _clear_overrides()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["subject"] == "MATH"
    assert first.json()["status"] == "OPEN"
    with postgres_session_factory() as session:
        assert session.query(LearningSession).filter_by(student_id=student.id).count() == 1


def test_first_authenticated_student_visit_creates_their_owned_math_session_with_zero_content(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    client = _client(postgres_session_factory, subject="first-student")
    try:
        response = client.post("/api/v1/student/math/session")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json()["subject"] == "MATH"
    assert response.json()["status"] == "OPEN"
    with postgres_session_factory() as session:
        user = session.query(User).filter_by(
            identity_provider="clerk", external_subject="first-student"
        ).one()
        student = session.query(Student).filter_by(user_id=user.id).one()
        assert session.query(LearningSession).filter_by(student_id=student.id).count() == 1


def test_zero_content_math_session_accepts_a_persisted_student_message(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Catches content readiness blocking a Student-owned Math message."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        session_id = learning_session.id
    client = _client(postgres_session_factory, subject="student-one")
    try:
        raw_message = client.post(
            f"/api/v1/student/math/session/{session_id}/messages",
            json={"content": "I tried one half."},
        )
    finally:
        _clear_overrides()

    assert raw_message.status_code == 200
    assert raw_message.json()["content"] == "I tried one half."
    with postgres_session_factory() as session:
        messages = session.query(LearningMessage).filter_by(session_id=session_id).all()
        assert [message.content for message in messages] == ["I tried one half."]


def test_authenticated_student_messages_are_persisted_in_order_and_restored_after_refresh(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        _ready_grade_five_math_content(session, student)

    client = _client(postgres_session_factory, subject="student-one")
    try:
        created = client.post("/api/v1/student/math/session")
        session_id = created.json()["id"]
        first = client.post(f"/api/v1/student/math/session/{session_id}/messages", json={"content": "I tried 4 × 25."})
        second = client.post(f"/api/v1/student/math/session/{session_id}/messages", json={"content": "Can I check my answer?"})
        refreshed = client.post("/api/v1/student/math/session")
    finally:
        _clear_overrides()

    assert first.status_code == 200
    assert second.status_code == 200
    assert refreshed.json()["id"] == session_id
    assert [message["content"] for message in refreshed.json()["messages"]] == [
        "I tried 4 × 25.",
        "Can I check my answer?",
    ]
    with postgres_session_factory() as session:
        messages = session.query(LearningMessage).order_by(LearningMessage.created_at, LearningMessage.id).all()
        assert [message.content for message in messages] == ["I tried 4 × 25.", "Can I check my answer?"]


def test_student_cannot_read_or_write_another_students_math_session(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        owner = _student(session, "student-owner")
        _student(session, "student-other")
        learning_session = LearningSession(student_id=owner.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        session_id = learning_session.id

    client = _client(postgres_session_factory, subject="student-other")
    try:
        read = client.get(f"/api/v1/student/math/session/{session_id}")
        write = client.post(
            f"/api/v1/student/math/session/{session_id}/messages",
            json={"content": "This must not be accepted."},
        )
    finally:
        _clear_overrides()

    assert read.status_code == 404
    assert write.status_code == 404
    with postgres_session_factory() as session:
        assert session.query(LearningMessage).filter_by(session_id=session_id).count() == 0


def test_student_session_path_has_no_automatic_close_side_effect(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        _ready_grade_five_math_content(session, student)

    client = _client(postgres_session_factory, subject="student-one")
    try:
        created = client.post("/api/v1/student/math/session")
        session_id = UUID(created.json()["id"])
        client.post(
            f"/api/v1/student/math/session/{session_id}/messages",
            json={"content": "I am continuing after a short break."},
        )
    finally:
        _clear_overrides()

    with postgres_session_factory() as session:
        persisted = session.get(LearningSession, session_id)
        assert persisted is not None
        assert persisted.status == "OPEN"
        assert persisted.closed_at is None


def test_failed_stream_keeps_the_student_message_and_failure_ledger_without_partial_tutor_output(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches the route rollback that erased the raw turn and its failed execution audit."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        session_id = learning_session.id

    from apps.api.routes import student as student_routes

    monkeypatch.setattr(student_routes, "create_tutor_runtime", _delta_then_failure_runtime)
    client = _client(postgres_session_factory, subject="student-one", raise_server_exceptions=False)
    try:
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "I need help with equivalent fractions."},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert "event: turn" not in response.text
    with postgres_session_factory() as session:
        messages = session.query(LearningMessage).filter_by(session_id=session_id).order_by(
            LearningMessage.created_at, LearningMessage.id
        ).all()
        assert [(message.role, message.content) for message in messages] == [
            ("student", "I need help with equivalent fractions."),
        ]
        execution = session.query(AIExecution).filter_by(task="tutor").one()
        assert execution.success is False
        assert execution.provider == "fixture-stream"
        assert execution.model == "fixture-failure-model"
        assert execution.failure_code == "RuntimeError"
        assert execution.student_id == student.id
        assert execution.learning_session_id == session_id
        assert execution.source_message_id == messages[0].id
        assert execution.operation_type == "tutor_turn"
        assert session.query(CandidateEvent).filter_by(session_id=session_id).count() == 0
        assert session.get(LearningSession, session_id).status == "OPEN"


def test_terminal_turn_is_emitted_only_after_its_suggested_action_source_is_committed(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UI-01: terminal SSE delivery must never race the next suggested-action request."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        session_id = learning_session.id

    from apps.api.routes import student as student_routes

    monkeypatch.setattr(student_routes, "create_tutor_runtime", _CommittedTurnFixtureRuntime)
    principal = AuthenticatedPrincipal(subject="student-one", role=UserRole.STUDENT, email="student-one@example.test")
    with postgres_session_factory() as route_session:
        response = student_routes.stream_math_tutor_turn(
            session_id=session_id,
            request=student_routes.StudentMessageRequest(content="Please help."),
            principal=principal,
            session=route_session,
        )

        async def terminal_event_source() -> tuple[str, UUID, UUID]:
            iterator = response.body_iterator
            try:
                first = await anext(iterator)
                assert "event: delta" in first
                terminal = await anext(iterator)
                with postgres_session_factory() as independent_session:
                    source_message = independent_session.query(LearningMessage).filter_by(
                        session_id=session_id,
                        role="tutor",
                    ).one()
                    resolved = latest_tutor_suggested_action(
                        independent_session,
                        learning_session=independent_session.get(LearningSession, session_id),
                        label="Give me a hint",
                    )
                assert resolved is not None
                return terminal, source_message.id, resolved.source_tutor_message_id
            finally:
                await iterator.aclose()

        terminal, source_message_id, resolved_source_message_id = asyncio.run(terminal_event_source())

    assert "event: turn" in terminal
    assert resolved_source_message_id == source_message_id


def test_a_session_recovers_with_a_successful_turn_after_a_failed_stream(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches failed-turn handling that leaves an open Student session unusable."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        session_id = learning_session.id

    from apps.api.routes import student as student_routes
    from services.tutor import runtime as tutor_runtime

    monkeypatch.setattr(student_routes, "create_tutor_runtime", _delta_then_failure_runtime)
    client = _client(postgres_session_factory, subject="student-one", raise_server_exceptions=False)
    try:
        failed = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "This first turn fails."},
        )
        monkeypatch.setattr(tutor_runtime, "get_settings", lambda: Settings(_env_file=None, model_provider="mock"))
        monkeypatch.setattr(student_routes, "create_tutor_runtime", tutor_runtime.create_tutor_runtime)
        recovered = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "Can we try equivalent fractions again?"},
        )
    finally:
        _clear_overrides()

    assert failed.status_code == 200
    assert "event: turn" not in failed.text
    assert recovered.status_code == 200
    assert "event: turn" in recovered.text
    with postgres_session_factory() as session:
        messages = session.query(LearningMessage).filter_by(session_id=session_id).order_by(
            LearningMessage.created_at, LearningMessage.id
        ).all()
        assert [(message.role, message.content) for message in messages] == [
            ("student", "This first turn fails."),
            ("student", "Can we try equivalent fractions again?"),
            ("tutor", "Let’s work on this step by step. Can we try equivalent fractions again?"),
        ]
        assert session.query(AIExecution).filter_by(task="tutor", success=False).count() == 1
        assert session.query(AIExecution).filter_by(task="tutor", success=True).count() == 1
        assert session.get(LearningSession, session_id).status == "OPEN"


def test_zero_content_student_tutor_turn_uses_empty_retrieval_and_persists_response(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        executions_before = session.query(AIExecution).filter_by(task="tutor").count()

    client = _client(postgres_session_factory, subject="student-one")
    from services.tutor import runtime as tutor_runtime

    monkeypatch.setattr(
        tutor_runtime,
        "get_settings",
        lambda: Settings(_env_file=None, model_provider="mock"),
    )
    try:
        created = client.post("/api/v1/student/math/session")
        session_id = created.json()["id"]
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "Explain equivalent fractions."},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: delta" in response.text
    assert "event: turn" in response.text
    assert "candidate" not in response.text
    final_event = response.text.split("event: turn\ndata: ", maxsplit=1)[1].split("\n\n", maxsplit=1)[0]
    assert json.loads(final_event) == {
        "text": "Let’s work on this step by step. Explain equivalent fractions.",
        "suggested_actions": [],
    }
    with postgres_session_factory() as session:
        messages = session.query(LearningMessage).filter_by(session_id=UUID(session_id)).order_by(LearningMessage.created_at, LearningMessage.id).all()
        assert [message.role for message in messages] == ["student", "tutor"]
        assert messages[-1].payload["source_refs"] == []
        assert messages[-1].payload["suggested_actions"] == []
        assert session.query(AIExecution).filter_by(task="tutor").count() == executions_before + 1


def test_session_reload_exposes_persisted_tutor_actions_and_defaults_legacy_messages_to_empty(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Catches a reload that either drops a Tutor action or invents one for a legacy message."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        session.add_all([
            LearningMessage(
                session_id=learning_session.id, role="tutor", content="جرّبي خطوة صغيرة.",
                payload={"suggested_actions": [{"label": "خليني أجرب ✍️", "kind": "NAVIGATION"}]},
            ),
            LearningMessage(session_id=learning_session.id, role="tutor", content="رسالة قديمة.", payload={}),
        ])
        session.flush()
        session_id = learning_session.id

    client = _client(postgres_session_factory, subject="student-one")
    try:
        response = client.get(f"/api/v1/student/math/session/{session_id}")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    actions_by_content = {
        message["content"]: message["suggested_actions"] for message in response.json()["messages"]
    }
    assert actions_by_content == {
        "جرّبي خطوة صغيرة.": [{"label": "خليني أجرب ✍️", "kind": "NAVIGATION"}],
        "رسالة قديمة.": [],
    }


def test_latest_tutor_suggested_action_retains_the_exact_tutor_source_identity(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """ACT-01: action acceptance returns the persisted Tutor provenance, not only its label/kind."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        source_message = LearningMessage(
            session_id=learning_session.id,
            role="tutor",
            content="6 stickers shared by 2 children: A) 2 B) 3 C) 4",
            payload={"suggested_actions": [{"label": "B) 3", "kind": "ANSWER_CHOICE"}]},
        )
        session.add(source_message)
        session.flush()

        resolved = latest_tutor_suggested_action(
            session,
            learning_session=learning_session,
            label="B) 3",
        )

    assert resolved is not None
    assert resolved.action.model_dump() == {"label": "B) 3", "kind": "ANSWER_CHOICE"}
    assert resolved.source_tutor_message_id == source_message.id


def test_server_derives_action_kind_from_latest_tutor_actions_and_rejects_stale_or_forged_claims(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches browser-supplied action semantics bypassing the latest persisted Tutor action set."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        source_message = LearningMessage(
            session_id=learning_session.id,
            role="tutor",
            content="Which fraction equals one half?",
            payload={"suggested_actions": [{"label": "2/4", "kind": "ANSWER_CHOICE"}]},
        )
        session.add(source_message)
        session.flush()
        session_id = learning_session.id

    from services.tutor import runtime as tutor_runtime

    monkeypatch.setattr(tutor_runtime, "get_settings", lambda: Settings(_env_file=None, model_provider="mock"))
    client = _client(postgres_session_factory, subject="student-one")
    try:
        valid = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "2/4", "suggested_action": True, "suggested_action_kind": "NAVIGATION"},
        )
    finally:
        _clear_overrides()

    assert valid.status_code == 200
    with postgres_session_factory() as session:
        student_message = session.query(LearningMessage).filter_by(session_id=session_id, role="student").one()
        assert student_message.payload["input_kind"] == "suggested_action_answer_choice"
        assert student_message.payload["suggested_action_source_tutor_message_id"] == str(source_message.id)

    with postgres_session_factory.begin() as session:
        session.add(
            LearningMessage(
                session_id=session_id,
                role="tutor",
                content="Tell me why you chose it.",
                payload={"suggested_actions": []},
            )
        )

    client = _client(postgres_session_factory, subject="student-one")
    try:
        stale = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "2/4", "suggested_action": True, "suggested_action_kind": "ANSWER_CHOICE"},
        )
    finally:
        _clear_overrides()

    assert stale.status_code == 422


def test_parent_redirect_stream_never_calls_the_tutor_model(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        executions_before = session.query(AIExecution).filter_by(task="tutor").count()

    client = _client(postgres_session_factory, subject="student-one")
    from services.tutor import runtime as tutor_runtime

    monkeypatch.setattr(tutor_runtime, "get_settings", lambda: Settings(_env_file=None, model_provider="mock"))
    try:
        session_id = client.post("/api/v1/student/math/session").json()["id"]
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "Can you explain prayer?"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert "event: delta" not in response.text
    assert "event: turn" in response.text
    with postgres_session_factory() as session:
        assert session.query(AIExecution).filter_by(task="tutor").count() == executions_before
