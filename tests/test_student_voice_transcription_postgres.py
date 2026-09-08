"""Production-boundary contracts for transient Student voice transcription."""

from __future__ import annotations

import os
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    AIExecution,
    ContentDocument,
    Job,
    LearnerIntelligenceCard,
    LearningEvidence,
    LearningEvent,
    LearningMessage,
    LearningSession,
    ModelTask,
    PersonalFact,
    StudioEvent,
    Student,
    User,
)
from services.platform.db.session import get_session


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Student transcription tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users, jobs CASCADE"))
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _student_and_session(
    factory: sessionmaker[Session], *, subject: str
) -> tuple[UUID, UUID]:
    with factory.begin() as session:
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
        learning_session = LearningSession(student_id=student.id, status="OPEN")
        session.add(learning_session)
        session.flush()
        return student.id, learning_session.id


def _client(
    factory: sessionmaker[Session],
    *,
    subject: str,
    role: UserRole = UserRole.STUDENT,
) -> TestClient:
    from apps.api.main import app

    def database_session():
        with factory.begin() as session:
            yield session

    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject=subject,
        role=role,
        email=f"{subject}@example.test",
    )
    return TestClient(app, raise_server_exceptions=False)


def _clear_overrides() -> None:
    from apps.api.main import app

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_principal, None)


class _TranscriptionProvider:
    def __init__(self, *, transcript: str = "الكسر one half", failure: Exception | None = None) -> None:
        self.transcript = transcript
        self.failure = failure
        self.call_count = 0
        self.payloads: list[dict[str, object]] = []

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        assert route == ModelRoute("fixture", "gpt-transcribe")
        self.call_count += 1
        self.payloads.append(payload)
        if self.failure is not None:
            raise self.failure
        return ModelResult(output={"transcript": self.transcript})


def _install_provider(monkeypatch: pytest.MonkeyPatch, provider: _TranscriptionProvider) -> None:
    import apps.api.routes.student as student_routes

    monkeypatch.setattr(
        student_routes,
        "create_student_transcription_gateway",
        lambda session: ModelGateway(
            session,
            routes={ModelTask.SPEECH_TO_TEXT: ModelRoute("fixture", "gpt-transcribe")},
            providers={"fixture": provider},
        ),
    )


def test_student_can_transcribe_owned_daily_audio_without_durable_audio_or_learning_side_effects(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = b"raw-audio-secret-marker"
    student_id, learning_session_id = _student_and_session(
        postgres_session_factory, subject="voice-owner"
    )
    provider = _TranscriptionProvider()
    _install_provider(monkeypatch, provider)
    client = _client(postgres_session_factory, subject="voice-owner")

    try:
        response = client.post(
            f"/api/v1/student/daily/session/{learning_session_id}/voice/transcribe",
            files={"audio": ("mixed phrase.webm", marker, "audio/webm")},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    execution_id = UUID(response.json()["transcription_execution_id"])
    assert response.json() == {
        "transcript": "الكسر one half",
        "transcription_execution_id": str(execution_id),
    }
    assert provider.call_count == 1
    assert provider.payloads == [
        {
            "audio": marker,
            "filename": "mixed_phrase.webm",
            "content_type": "audio/webm",
        }
    ]

    with postgres_session_factory() as session:
        execution = session.get(AIExecution, execution_id)
        assert execution is not None
        assert execution.task == "speech_to_text"
        assert execution.provider == "fixture"
        assert execution.model == "gpt-transcribe"
        assert execution.success is True
        assert execution.operation_type == "speech_to_text"
        assert execution.student_id == student_id
        assert execution.learning_session_id == learning_session_id
        assert execution.input_tokens is None
        assert execution.output_tokens is None
        assert execution.estimated_cost_usd is None
        assert session.query(AIExecution).count() == 1
        for model in (
            LearningMessage,
            Job,
            StudioEvent,
            LearningEvent,
            LearningEvidence,
            PersonalFact,
            LearnerIntelligenceCard,
            ContentDocument,
        ):
            assert session.query(model).count() == 0
        serialized_rows = "\n".join(
            str(row)
            for table in ("ai_executions", "jobs", "learning_messages", "studio_events")
            for row in session.execute(text(f"SELECT * FROM {table}")).all()
        )
        assert marker.decode() not in serialized_rows


@pytest.mark.parametrize(
    "filename,content_type,audio,status_code",
    [
        ("empty.webm", "audio/webm", b"", 422),
        ("voice.txt", "text/plain", b"words", 415),
        ("huge.wav", "audio/wav", b"x" * (5 * 1024 * 1024 + 1), 413),
    ],
    ids=("empty", "unsupported-media", "oversized"),
)
def test_student_audio_is_rejected_before_provider_attempt(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content_type: str,
    audio: bytes,
    status_code: int,
) -> None:
    _, learning_session_id = _student_and_session(
        postgres_session_factory, subject="voice-validation"
    )
    provider = _TranscriptionProvider()
    _install_provider(monkeypatch, provider)
    client = _client(postgres_session_factory, subject="voice-validation")

    try:
        response = client.post(
            f"/api/v1/student/daily/session/{learning_session_id}/voice/transcribe",
            files={"audio": (filename, audio, content_type)},
        )
    finally:
        _clear_overrides()

    assert response.status_code == status_code
    assert provider.call_count == 0
    with postgres_session_factory() as session:
        assert session.query(AIExecution).count() == 0


def test_student_cannot_transcribe_another_students_session(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, learning_session_id = _student_and_session(
        postgres_session_factory, subject="different-owner"
    )
    _student_and_session(postgres_session_factory, subject="voice-caller")
    provider = _TranscriptionProvider()
    _install_provider(monkeypatch, provider)
    client = _client(postgres_session_factory, subject="voice-caller")

    try:
        response = client.post(
            f"/api/v1/student/daily/session/{learning_session_id}/voice/transcribe",
            files={"audio": ("voice.wav", b"RIFFdata", "audio/wav")},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 404
    assert provider.call_count == 0
    with postgres_session_factory() as session:
        assert session.query(AIExecution).count() == 0


def test_non_student_principal_cannot_use_student_transcription(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, learning_session_id = _student_and_session(
        postgres_session_factory, subject="voice-role-owner"
    )
    provider = _TranscriptionProvider()
    _install_provider(monkeypatch, provider)
    client = _client(
        postgres_session_factory,
        subject="voice-role-owner",
        role=UserRole.PARENT_ADMIN,
    )

    try:
        response = client.post(
            f"/api/v1/student/daily/session/{learning_session_id}/voice/transcribe",
            files={"audio": ("voice.webm", b"audio", "audio/webm")},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 403
    assert provider.call_count == 0
    with postgres_session_factory() as session:
        assert session.query(AIExecution).count() == 0


def test_provider_failure_returns_safe_error_and_commits_one_failed_execution(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.model_gateway.openai_transcription_provider import TranscriptionProviderError

    student_id, learning_session_id = _student_and_session(
        postgres_session_factory, subject="voice-failure"
    )
    provider = _TranscriptionProvider(failure=TranscriptionProviderError("network_error"))
    _install_provider(monkeypatch, provider)
    client = _client(postgres_session_factory, subject="voice-failure")

    try:
        response = client.post(
            f"/api/v1/student/daily/session/{learning_session_id}/voice/transcribe",
            files={"audio": ("voice.webm", b"private raw audio", "audio/webm")},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 502
    assert response.json() == {"detail": "Voice transcription is temporarily unavailable."}
    assert provider.call_count == 1
    with postgres_session_factory() as session:
        execution = session.query(AIExecution).one()
        assert execution.task == "speech_to_text"
        assert execution.success is False
        assert execution.failure_code == "TranscriptionProviderError"
        assert execution.operation_type == "speech_to_text"
        assert execution.student_id == student_id
        assert execution.learning_session_id == learning_session_id
        assert session.query(LearningMessage).count() == 0
