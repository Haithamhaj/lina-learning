"""PostgreSQL contract tests for the authenticated Student Math session path."""

from __future__ import annotations

import asyncio
import json
import os
from types import SimpleNamespace
from threading import Event, Thread
from time import monotonic
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
    LearningEvidence,
    LearningEvent,
    LearnerIntelligenceCard,
    LearningSession,
    SafetyAudit,
    StudioRuntime,
    StudioTutorObservation,
    Student,
    User,
)
from services.platform.db.session import get_session
from services.platform.config import Settings
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.db.models import ModelTask
from services.platform.safety import SafetyPolicyService
from services.retrieval.service import RetrievalService
from services.studio.contracts import AppendStudioEventCommand, StudioActor
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import StudioStateService
from services.tutor.capacity import TutorContextCapacityExceeded, TutorContextCapacityLineage
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


class _ImmediateSuccessfulTutorProvider:
    """Deterministic one-call provider for the real Tutor streaming route."""

    def __init__(self) -> None:
        self.called = Event()
        self.call_count = 0
        self.payloads: list[dict[str, object]] = []

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route
        self.call_count += 1
        self.payloads.append(payload)
        self.called.set()
        text = "Keep the denominator and add the numerators."
        yield StreamDelta(text)
        yield StreamComplete(ModelResult(
            output={
                "text": text,
                "suggested_actions": [],
                "guided_check": None,
                "teaching_mode": None,
                "teaching_strategy": None,
                "teaching_method_id": None,
                "prior_method_relation": None,
                "candidate_metadata": None,
                "provisional_broad_subject": None,
                "segment_relation": None,
                "structured_segment_state": None,
            },
            input_tokens=4,
            output_tokens=3,
        ))


class _BlockingTutorProvider(_ImmediateSuccessfulTutorProvider):
    """Holds the one primary provider call so a concurrent Studio append is observable."""

    def __init__(self) -> None:
        super().__init__()
        self.release = Event()

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route
        self.call_count += 1
        self.payloads.append(payload)
        self.called.set()
        assert self.release.wait(timeout=5), "test must release the primary Tutor provider"
        text = "Keep the denominator and add the numerators."
        yield StreamDelta(text)
        yield StreamComplete(ModelResult(
            output={
                "text": text,
                "suggested_actions": [],
                "guided_check": None,
                "teaching_mode": None,
                "teaching_strategy": None,
                "teaching_method_id": None,
                "prior_method_relation": None,
                "candidate_metadata": None,
                "provisional_broad_subject": None,
                "segment_relation": None,
                "structured_segment_state": None,
            },
            input_tokens=4,
            output_tokens=3,
        ))


class _CandidateMetadataTutorProvider:
    """One primary-call fixture that attempts to turn a clicked action into an attempt Candidate."""

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route
        source_message_id = str(payload["candidate_source_message_id"])
        result = ModelResult(
            output={
                "text": "Okay, let’s continue.",
                "suggested_actions": [],
                "teaching_mode": None,
                "teaching_strategy": None,
                "teaching_method_id": None,
                "prior_method_relation": None,
                "candidate_metadata": {
                    "version": "candidate-event-v1",
                    "candidates": [{
                        "event_type": "learning_attempt",
                        "concept_ref": "decimals",
                        "summary": "The Student selected a decimals action.",
                        "signal": "selected_decimals_action",
                        "source_message_ids": [source_message_id],
                        "school_or_extended": "school",
                    }],
                },
            },
            input_tokens=4,
            output_tokens=3,
        )
        yield StreamDelta("Okay, let’s continue.")
        yield StreamComplete(result)


def _candidate_metadata_runtime(session: Session) -> TutorRuntime:
    return TutorRuntime(
        session,
        context_builder=TutorContextBuilder(session, retrieval_service=RetrievalService(session)),
        safety_policy=SafetyPolicyService(session),
        gateway=ModelGateway(
            session,
            routes={ModelTask.TUTOR: ModelRoute("fixture-candidate", "fixture-candidate-model")},
            providers={"fixture-candidate": _CandidateMetadataTutorProvider()},
        ),
    )


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


def _successful_streaming_runtime(provider: _ImmediateSuccessfulTutorProvider):
    def create(session: Session) -> TutorRuntime:
        return TutorRuntime(
            session,
            context_builder=TutorContextBuilder(session, retrieval_service=RetrievalService(session)),
            safety_policy=SafetyPolicyService(session),
            gateway=ModelGateway(
                session,
                routes={ModelTask.TUTOR: ModelRoute("fixture-stream", "fixture-success-model")},
                providers={"fixture-stream": provider},
            ),
        )

    return create


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


class _CapacityFailureFixtureRuntime:
    """Model no-call failure after the raw Student turn has been accepted."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def stream_turn(self, *, learning_session: LearningSession, question: str, **_: object):
        self._session.add(LearningMessage(session_id=learning_session.id, role="student", content=question))
        self._session.flush()
        raise TutorContextCapacityExceeded(
            TutorContextCapacityLineage(
                capacity_limit=1,
                initial_measured_size=2,
                final_measured_size=2,
                selected_context={},
                kept_context={},
                dropped_context=(),
            )
        )
        yield  # pragma: no cover - makes this a generator fixture


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
        runtime = StudioStateService(session).get_or_create_runtime(
            student_id=student.id,
            learning_session_id=learning_session.id,
        )
        StudioStateService(session).append_event(
            AppendStudioEventCommand(
                runtime_id=runtime.id,
                student_id=student.id,
                learning_session_id=learning_session.id,
                event_kind="studio.runtime.initialized",
                event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                actor=StudioActor.SYSTEM,
                payload_schema_version="studio-runtime-initialized-v1",
                payload={},
                idempotency_key="failed-stream-studio-1",
            )
        )
        session_id, runtime_id = learning_session.id, runtime.id

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
        observation = session.query(StudioTutorObservation).one()
        runtime = session.get(StudioRuntime, runtime_id)
        assert observation.status == "FAILED"
        assert observation.failure_metadata == {"code": "PROVIDER_FAILURE"}
        assert runtime is not None and runtime.last_tutor_observation_sequence == 0


def test_capacity_failure_keeps_the_accepted_student_turn_without_a_model_execution(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches capacity overflow rolling back a raw turn or fabricating a failed Tutor execution."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        session_id = learning_session.id

    from apps.api.routes import student as student_routes

    monkeypatch.setattr(student_routes, "create_tutor_runtime", _CapacityFailureFixtureRuntime)
    client = _client(postgres_session_factory, subject="student-one", raise_server_exceptions=False)
    try:
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "I need help with a very long question."},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert "event: turn" not in response.text
    with postgres_session_factory() as session:
        messages = session.query(LearningMessage).filter_by(session_id=session_id).all()
        assert [(message.role, message.content) for message in messages] == [
            ("student", "I need help with a very long question."),
        ]
        assert session.query(AIExecution).filter_by(task="tutor").count() == 0
        assert session.query(CandidateEvent).filter_by(session_id=session_id).count() == 0
        assert session.query(LearningEvent).filter_by(session_id=session_id).count() == 0
        assert session.query(LearningEvidence).count() == 0
        assert session.query(LearnerIntelligenceCard).filter_by(student_id=student.id).count() == 0


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


def test_streaming_route_releases_request_student_lock_before_safety_audit_and_model_call(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches the request-owned Student lock blocking the stream-owned SafetyAudit FK insert."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        session_id = learning_session.id

    from apps.api.routes import student as student_routes

    provider = _ImmediateSuccessfulTutorProvider()
    monkeypatch.setattr(student_routes, "create_tutor_runtime", _successful_streaming_runtime(provider))
    principal = AuthenticatedPrincipal(subject="student-one", role=UserRole.STUDENT, email="student-one@example.test")
    request_session = postgres_session_factory()
    response = student_routes.stream_math_tutor_turn(
        session_id=session_id,
        request=student_routes.StudentMessageRequest(content="How do I add 3/4 and 1/4?"),
        principal=principal,
        session=request_session,
    )
    chunks: list[str] = []
    thread_errors: list[BaseException] = []

    async def drain() -> None:
        iterator = response.body_iterator
        try:
            async for chunk in iterator:
                chunks.append(chunk.decode() if isinstance(chunk, bytes) else str(chunk))
        except BaseException as error:
            thread_errors.append(error)
        finally:
            await iterator.aclose()

    thread = Thread(target=lambda: asyncio.run(drain()))
    started = monotonic()
    thread.start()
    try:
        assert provider.called.wait(timeout=0.5), "the stream must reach SafetyAudit and the one primary provider call without waiting for the request transaction"
    finally:
        request_session.commit()
        request_session.close()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert thread_errors == []
    assert monotonic() - started < 0.5
    assert provider.call_count == 1
    assert "event: turn" in "".join(chunks)
    with postgres_session_factory() as session:
        messages = session.query(LearningMessage).filter_by(session_id=session_id).order_by(
            LearningMessage.created_at, LearningMessage.id
        ).all()
        assert [message.role for message in messages] == ["student", "tutor"]
        assert session.query(SafetyAudit).filter_by(student_id=student.id).count() == 1
        execution = session.query(AIExecution).filter_by(
            learning_session_id=session_id,
            task=ModelTask.TUTOR.value,
        ).one()
        assert execution.success is True
        assert execution.provider == "fixture-stream"


def test_normal_chat_turn_observes_studio_in_its_one_primary_call_then_acknowledges(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful terminal SSE commits exactly the selected Studio range after Chat persistence."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-studio-observation")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(
            student_id=student.id,
            learning_session_id=learning_session.id,
        )
        StudioStateService(session).append_event(
            AppendStudioEventCommand(
                runtime_id=runtime.id,
                student_id=student.id,
                learning_session_id=learning_session.id,
                event_kind="studio.runtime.initialized",
                event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                actor=StudioActor.SYSTEM,
                payload_schema_version="studio-runtime-initialized-v1",
                payload={},
                idempotency_key="chat-studio-observation-1",
            )
        )
        session_id, runtime_id, student_id = learning_session.id, runtime.id, student.id

    from apps.api.routes import student as student_routes

    provider = _ImmediateSuccessfulTutorProvider()
    monkeypatch.setattr(student_routes, "create_tutor_runtime", _successful_streaming_runtime(provider))
    client = _client(postgres_session_factory, subject="student-studio-observation")
    try:
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "I just worked in the Studio."},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert "event: turn" in response.text
    assert provider.call_count == 1
    assert "Studio Workspace Context" in str(provider.payloads[0]["input"])
    assert '"through_sequence": 1' in str(provider.payloads[0]["input"])
    with postgres_session_factory() as session:
        observation = session.query(StudioTutorObservation).one()
        runtime = session.get(StudioRuntime, runtime_id)
        execution = session.query(AIExecution).filter_by(learning_session_id=session_id, task="tutor").one()
        student_message = session.query(LearningMessage).filter_by(session_id=session_id, role="student").one()
        tutor_message = session.query(LearningMessage).filter_by(session_id=session_id, role="tutor").one()
        assert observation.status == "COMMITTED"
        assert observation.ai_execution_id == execution.id
        assert execution.student_id == student_id
        assert execution.learning_session_id == session_id
        assert execution.task == ModelTask.TUTOR.value
        assert execution.success is True
        assert execution.source_message_id == student_message.id
        assert session.query(AIExecution).filter_by(learning_session_id=session_id).count() == 1
        assert runtime is not None and runtime.last_tutor_observation_sequence == 1
        assert session.query(CandidateEvent).filter_by(session_id=session_id).count() == 0
        assert session.query(LearningEvent).filter_by(session_id=session_id).count() == 0
        assert session.query(LearningEvidence).count() == 0
        assert tutor_message.payload["context_debug"]["studio"] == {
            "included": True,
            "context_schema_version": "studio-tutor-context-v1",
            "runtime_id": str(runtime_id),
            "snapshot_sequence": 1,
            "observation_id": str(observation.id),
            "from_sequence": 1,
            "through_sequence": 1,
            "selected_event_sequences": [1],
        }


def test_idle_studio_runtime_still_supplies_snapshot_without_creating_observation(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An active but unchanged Studio remains current context without pretending a new action occurred."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-studio-idle")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        session_id, runtime_id = learning_session.id, runtime.id

    from apps.api.routes import student as student_routes

    provider = _ImmediateSuccessfulTutorProvider()
    monkeypatch.setattr(student_routes, "create_tutor_runtime", _successful_streaming_runtime(provider))
    client = _client(postgres_session_factory, subject="student-studio-idle")
    try:
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "Can you see my current Studio?"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert provider.call_count == 1
    assert '"through_sequence": 0' in str(provider.payloads[0]["input"])
    assert '"unseen_events": []' in str(provider.payloads[0]["input"])
    with postgres_session_factory() as session:
        runtime = session.get(StudioRuntime, runtime_id)
        assert runtime is not None and runtime.last_tutor_observation_sequence == 0
        assert session.query(StudioTutorObservation).count() == 0


def test_studio_capacity_failure_marks_selected_observation_without_calling_provider(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole selected Studio range stays unseen when protected request capacity is exceeded."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-studio-capacity")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        StudioStateService(session).append_event(
            AppendStudioEventCommand(
                runtime_id=runtime.id, student_id=student.id, learning_session_id=learning_session.id,
                event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                actor=StudioActor.SYSTEM, payload_schema_version="studio-runtime-initialized-v1", payload={},
                idempotency_key="chat-studio-capacity-1",
            )
        )
        session_id, runtime_id = learning_session.id, runtime.id

    from apps.api.routes import student as student_routes
    from services.tutor import runtime as tutor_runtime

    provider = _ImmediateSuccessfulTutorProvider()
    observed_failures: list[dict[str, object]] = []
    original_mark_failed = tutor_runtime.mark_studio_tutor_observation_failed

    def record_failure(**kwargs: object) -> None:
        observed_failures.append(kwargs)
        original_mark_failed(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(student_routes, "create_tutor_runtime", _successful_streaming_runtime(provider))
    monkeypatch.setattr(
        tutor_runtime,
        "get_settings",
        lambda: SimpleNamespace(tutor_context_capacity=1, tutor_max_output_tokens=2000),
    )
    monkeypatch.setattr(tutor_runtime, "mark_studio_tutor_observation_failed", record_failure)
    client = _client(postgres_session_factory, subject="student-studio-capacity", raise_server_exceptions=False)
    try:
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "Please help with this Studio step."},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert "event: turn" not in response.text
    assert provider.call_count == 0
    assert len(observed_failures) == 1
    with postgres_session_factory() as session:
        observation = session.query(StudioTutorObservation).one()
        runtime = session.get(StudioRuntime, runtime_id)
        assert observation.status == "FAILED"
        assert observation.failure_metadata == {"code": "CAPACITY_EXCEEDED"}
        assert runtime is not None and runtime.last_tutor_observation_sequence == 0


def test_studio_append_during_primary_tutor_generation_is_not_blocked_or_acknowledged_early(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The short selection lock releases before the provider, leaving the appended suffix for next turn."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-studio-concurrency")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        StudioStateService(session).append_event(
            AppendStudioEventCommand(
                runtime_id=runtime.id, student_id=student.id, learning_session_id=learning_session.id,
                event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                actor=StudioActor.SYSTEM, payload_schema_version="studio-runtime-initialized-v1", payload={},
                idempotency_key="chat-studio-concurrency-1",
            )
        )
        session_id, runtime_id, student_id = learning_session.id, runtime.id, student.id

    from apps.api.routes import student as student_routes
    from services.studio.tutor_context import select_studio_tutor_context

    provider = _BlockingTutorProvider()
    monkeypatch.setattr(student_routes, "create_tutor_runtime", _successful_streaming_runtime(provider))
    principal = AuthenticatedPrincipal(
        subject="student-studio-concurrency", role=UserRole.STUDENT,
        email="student-studio-concurrency@example.test",
    )
    request_session = postgres_session_factory()
    response = student_routes.stream_math_tutor_turn(
        session_id=session_id,
        request=student_routes.StudentMessageRequest(content="Please look at my current Studio work."),
        principal=principal,
        session=request_session,
    )
    chunks: list[str] = []
    errors: list[BaseException] = []

    async def drain() -> None:
        iterator = response.body_iterator
        try:
            async for chunk in iterator:
                chunks.append(chunk.decode() if isinstance(chunk, bytes) else str(chunk))
        except BaseException as error:
            errors.append(error)
        finally:
            await iterator.aclose()

    streaming = Thread(target=lambda: asyncio.run(drain()))
    streaming.start()
    try:
        assert provider.called.wait(timeout=1), "the single primary Tutor provider must begin"
        append_finished = Event()
        append_errors: list[BaseException] = []

        def append_later_event() -> None:
            try:
                with postgres_session_factory.begin() as session:
                    StudioStateService(session).append_event(
                        AppendStudioEventCommand(
                            runtime_id=runtime_id, student_id=student_id, learning_session_id=session_id,
                            event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                            actor=StudioActor.SYSTEM, payload_schema_version="studio-runtime-initialized-v1", payload={},
                            idempotency_key="chat-studio-concurrency-2",
                        )
                    )
            except BaseException as error:
                append_errors.append(error)
            finally:
                append_finished.set()

        append_thread = Thread(target=append_later_event)
        append_thread.start()
        assert append_finished.wait(timeout=1), "Studio append must not wait for the primary Tutor provider"
        append_thread.join(timeout=1)
        assert append_errors == []
        assert '"through_sequence": 1' in str(provider.payloads[0]["input"])
        assert '"sequence": 2' not in str(provider.payloads[0]["input"])
        provider.release.set()
    finally:
        request_session.close()
        streaming.join(timeout=5)

    assert not streaming.is_alive()
    assert errors == []
    assert "event: turn" in "".join(chunks)
    with postgres_session_factory() as session:
        runtime = session.get(StudioRuntime, runtime_id)
        observation = session.query(StudioTutorObservation).one()
        assert runtime is not None and runtime.latest_event_sequence == 2
        assert runtime.last_tutor_observation_sequence == 1
        assert observation.status == "COMMITTED" and observation.through_event_sequence == 1
    with postgres_session_factory() as session:
        engine = session.get_bind()
    next_selection = select_studio_tutor_context(bind=engine, student_id=student_id, learning_session_id=session_id)
    assert next_selection is not None
    assert [event.sequence for event in next_selection.context.unseen_events] == [2]


def test_terminal_persistence_failure_marks_studio_observation_failed_without_advancing(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A validated provider terminal result is not a successful Studio observation until Tutor persistence succeeds."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-studio-terminal-failure")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        StudioStateService(session).append_event(
            AppendStudioEventCommand(
                runtime_id=runtime.id, student_id=student.id, learning_session_id=learning_session.id,
                event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                actor=StudioActor.SYSTEM, payload_schema_version="studio-runtime-initialized-v1", payload={},
                idempotency_key="chat-studio-terminal-failure-1",
            )
        )
        session_id, runtime_id = learning_session.id, runtime.id

    from apps.api.routes import student as student_routes

    def fail_tutor_persistence(*_: object, **__: object) -> TutorTurn:
        raise RuntimeError("fixture terminal persistence failure")

    provider = _ImmediateSuccessfulTutorProvider()
    monkeypatch.setattr(student_routes, "create_tutor_runtime", _successful_streaming_runtime(provider))
    monkeypatch.setattr(TutorRuntime, "_persist_completed_turn", fail_tutor_persistence)
    client = _client(postgres_session_factory, subject="student-studio-terminal-failure", raise_server_exceptions=False)
    try:
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "Please help with this Studio step."},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert provider.call_count == 1
    assert "event: turn" not in response.text
    with postgres_session_factory() as session:
        observation = session.query(StudioTutorObservation).one()
        runtime = session.get(StudioRuntime, runtime_id)
        assert observation.status == "FAILED"
        assert observation.failure_metadata == {"code": "TERMINAL_FAILURE"}
        assert runtime is not None and runtime.last_tutor_observation_sequence == 0


def test_terminal_stream_interruption_leaves_selected_studio_range_unacknowledged_for_reselection(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Closing the SSE generator at its terminal yield never consumes Studio Events prematurely."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-studio-interrupted-terminal")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        StudioStateService(session).append_event(
            AppendStudioEventCommand(
                runtime_id=runtime.id, student_id=student.id, learning_session_id=learning_session.id,
                event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                actor=StudioActor.SYSTEM, payload_schema_version="studio-runtime-initialized-v1", payload={},
                idempotency_key="chat-studio-interrupted-terminal-1",
            )
        )
        session_id, runtime_id, student_id = learning_session.id, runtime.id, student.id

    from apps.api.routes import student as student_routes
    from services.studio.tutor_context import select_studio_tutor_context

    provider = _ImmediateSuccessfulTutorProvider()
    monkeypatch.setattr(student_routes, "create_tutor_runtime", _successful_streaming_runtime(provider))
    principal = AuthenticatedPrincipal(
        subject="student-studio-interrupted-terminal", role=UserRole.STUDENT,
        email="student-studio-interrupted-terminal@example.test",
    )
    with postgres_session_factory() as route_session:
        response = student_routes.stream_math_tutor_turn(
            session_id=session_id,
            request=student_routes.StudentMessageRequest(content="Please help with this Studio step."),
            principal=principal,
            session=route_session,
        )

        async def stop_at_terminal() -> None:
            iterator = response.body_iterator
            try:
                first = await anext(iterator)
                assert "event: delta" in first
                terminal = await anext(iterator)
                assert "event: turn" in terminal
            finally:
                await iterator.aclose()

        asyncio.run(stop_at_terminal())

    with postgres_session_factory() as session:
        runtime = session.get(StudioRuntime, runtime_id)
        observation = session.query(StudioTutorObservation).one()
        engine = session.get_bind()
        assert runtime is not None and runtime.last_tutor_observation_sequence == 0
        assert observation.status in {"SELECTED", "CANCELLED"}
    replacement = select_studio_tutor_context(bind=engine, student_id=student_id, learning_session_id=session_id)
    assert replacement is not None
    assert [event.sequence for event in replacement.context.unseen_events] == [1]


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
        "guided_check": None,
    }
    with postgres_session_factory() as session:
        messages = session.query(LearningMessage).filter_by(session_id=UUID(session_id)).order_by(LearningMessage.created_at, LearningMessage.id).all()
        assert [message.role for message in messages] == ["student", "tutor"]
        assert session.query(StudioRuntime).filter_by(learning_session_id=UUID(session_id)).count() == 0
        assert session.query(StudioTutorObservation).count() == 0
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
        assert student_message.payload["input_kind"] == "suggested_action"
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


def test_semantic_navigation_mislabeled_as_answer_choice_never_persists_a_candidate(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ACT-02: a persisted model kind cannot make topic navigation into learning evidence."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        session.add(
            LearningMessage(
                session_id=learning_session.id,
                role="tutor",
                content="What would you like to do next?",
                payload={"suggested_actions": [{
                    "label": "Let's learn decimals instead",
                    "kind": "ANSWER_CHOICE",
                }]},
            )
        )
        session_id = learning_session.id

    from apps.api.routes import student as student_routes
    from services.tutor import runtime as tutor_runtime

    monkeypatch.setattr(student_routes, "create_tutor_runtime", _candidate_metadata_runtime)
    monkeypatch.setattr(tutor_runtime, "get_settings", lambda: Settings(_env_file=None, model_provider="mock"))
    client = _client(postgres_session_factory, subject="student-one")
    try:
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "Let's learn decimals instead", "suggested_action": True},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    with postgres_session_factory() as session:
        student_message = session.query(LearningMessage).filter_by(session_id=session_id, role="student").one()
        assert student_message.payload["input_kind"] == "suggested_action"
        assert session.query(CandidateEvent).filter_by(session_id=session_id).count() == 0


def test_valid_persisted_guided_check_choice_can_persist_a_bounded_attempt_candidate(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ACT-02: the server grants click eligibility only after exact persisted check membership validates."""

    guided_check_id = UUID(int=31)
    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        session.add(
            LearningMessage(
                session_id=learning_session.id,
                role="tutor",
                content="6 ÷ 2 = ?",
                payload={"guided_check": {
                    "id": str(guided_check_id),
                    "prompt": "6 ÷ 2 = ?",
                    "choices": [{"label": "A) 2"}, {"label": "B) 3"}, {"label": "C) 4"}],
                }},
            )
        )
        session_id = learning_session.id

    from apps.api.routes import student as student_routes
    from services.tutor import runtime as tutor_runtime

    monkeypatch.setattr(student_routes, "create_tutor_runtime", _candidate_metadata_runtime)
    monkeypatch.setattr(tutor_runtime, "get_settings", lambda: Settings(_env_file=None, model_provider="mock"))
    client = _client(postgres_session_factory, subject="student-one")
    try:
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "B) 3", "guided_check_id": str(guided_check_id)},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    with postgres_session_factory() as session:
        student_message = session.query(LearningMessage).filter_by(session_id=session_id, role="student").one()
        assert student_message.payload["input_kind"] == "guided_learning_check_answer"
        assert student_message.payload["guided_check_id"] == str(guided_check_id)
        assert session.query(CandidateEvent).filter_by(session_id=session_id).count() == 1


@pytest.mark.parametrize(
    ("submitted_check_id", "content"),
    [
        (UUID(int=32), "B) 3"),
        (UUID(int=31), "D) 5"),
    ],
    ids=["forged-check-id", "choice-outside-persisted-check"],
)
def test_unbound_or_forged_guided_check_click_is_rejected_before_candidate_persistence(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    submitted_check_id: UUID,
    content: str,
) -> None:
    """ACT-02: a request cannot forge a check identity or choose outside its exact persisted choices."""

    persisted_check_id = UUID(int=31)
    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        session.add(
            LearningMessage(
                session_id=learning_session.id,
                role="tutor",
                content="6 ÷ 2 = ?",
                payload={"guided_check": {
                    "id": str(persisted_check_id),
                    "prompt": "6 ÷ 2 = ?",
                    "choices": [{"label": "A) 2"}, {"label": "B) 3"}, {"label": "C) 4"}],
                }},
            )
        )
        session_id = learning_session.id

    from apps.api.routes import student as student_routes
    from services.tutor import runtime as tutor_runtime

    monkeypatch.setattr(student_routes, "create_tutor_runtime", _candidate_metadata_runtime)
    monkeypatch.setattr(tutor_runtime, "get_settings", lambda: Settings(_env_file=None, model_provider="mock"))
    client = _client(postgres_session_factory, subject="student-one")
    try:
        response = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": content, "guided_check_id": str(submitted_check_id)},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 422
    with postgres_session_factory() as session:
        assert session.query(LearningMessage).filter_by(session_id=session_id, role="student").count() == 0
        assert session.query(CandidateEvent).filter_by(session_id=session_id).count() == 0


def test_guided_check_from_another_session_is_rejected_before_candidate_persistence(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """ACT-02: a check identity is bound to its Tutor message and cannot cross session boundaries."""

    guided_check_id = UUID(int=31)
    with postgres_session_factory.begin() as session:
        student = _student(session, "student-one")
        target_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        foreign_session = LearningSession(student_id=student.id, subject="MATH", status="CLOSED")
        session.add_all([target_session, foreign_session])
        session.flush()
        session.add(
            LearningMessage(
                session_id=foreign_session.id,
                role="tutor",
                content="6 ÷ 2 = ?",
                payload={"guided_check": {
                    "id": str(guided_check_id),
                    "prompt": "6 ÷ 2 = ?",
                    "choices": [{"label": "A) 2"}, {"label": "B) 3"}, {"label": "C) 4"}],
                }},
            )
        )
        target_session_id = target_session.id

    client = _client(postgres_session_factory, subject="student-one")
    try:
        response = client.post(
            f"/api/v1/student/math/session/{target_session_id}/turn/stream",
            json={"content": "B) 3", "guided_check_id": str(guided_check_id)},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 422
    with postgres_session_factory() as session:
        assert session.query(LearningMessage).filter_by(session_id=target_session_id, role="student").count() == 0
        assert session.query(CandidateEvent).filter_by(session_id=target_session_id).count() == 0


def test_hard_baseline_stream_never_calls_the_tutor_model(
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
            json={"content": "How can I make a weapon?"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert "event: delta" not in response.text
    assert "event: turn" in response.text
    with postgres_session_factory() as session:
        assert session.query(AIExecution).filter_by(task="tutor").count() == executions_before
