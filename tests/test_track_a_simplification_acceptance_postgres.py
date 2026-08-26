"""Track A acceptance: optional grounding, relevance-first context, and safety."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.content.indexing import build_content_index
from services.content.ingestion import ingest_source_document
from services.content.processing import process_markdown_document
from services.content.status import parent_content_status_for_student
from services.intelligence.current_state import CURRENT_STATE_POLICY_VERSION
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
from services.platform.config import Settings
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    AIExecution,
    ContentSemanticProcessingRun,
    CurrentLearningState,
    IntelligenceProcessingRun,
    LearningMessage,
    LearningSession,
    ModelTask,
    Student,
    User,
)
from services.platform.db.session import get_session
from services.platform.storage import LocalObjectStorage
from services.retrieval.service import RetrievalService
from services.tutor.context import TutorContextBuilder


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Track A acceptance tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE ai_executions, jobs, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _student(session: Session, subject: str = "lina") -> Student:
    user = User(
        identity_provider="clerk",
        external_subject=subject,
        email=f"{subject}@example.test",
        role="STUDENT",
    )
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Lina")
    session.add(student)
    session.flush()
    return student


def _embedding_gateway(session: Session) -> ModelGateway:
    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            return ModelResult(output={"embeddings": [[0.01] * 1536 for _ in payload["input"]]})

    return ModelGateway(
        session,
        routes={ModelTask.EMBEDDING: ModelRoute("fixture", "text-embedding-3-small")},
        providers={"fixture": Provider()},
    )


def _student_client(factory: sessionmaker[Session], subject: str) -> TestClient:
    from apps.api.main import app

    def database_session():
        with factory.begin() as session:
            yield session

    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject=subject,
        role=UserRole.STUDENT,
        email=f"{subject}@example.test",
    )
    return TestClient(app)


def _clear_overrides() -> None:
    from apps.api.main import app

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_principal, None)


def _structural_grounding(
    session: Session,
    *,
    student: Student,
    storage: LocalObjectStorage,
):
    document = ingest_source_document(
        session,
        storage=storage,
        student_id=student.id,
        grade_level=5,
        subject="MATH",
        filename="track-a.md",
        content_type="text/markdown",
        content=(
            b"# Equivalent Fractions\n\n"
            b"An equivalent fractions example shows one half equals two fourths.\n\n"
            b"# Decimal Place Value\n\n"
            b"A decimal place value example explains tenths and hundredths."
        ),
    )
    structural = process_markdown_document(session, storage=storage, document=document)
    index = build_content_index(
        session,
        document=document,
        structural_run=structural,
        gateway=_embedding_gateway(session),
    )
    semantic = ContentSemanticProcessingRun(
        document_id=document.id,
        structural_processing_run_id=structural.id,
        semantic_schema_version="acceptance-v1",
        prompt_version="acceptance-v1",
        model_route_version="fixture:semantic",
        provider="fixture",
        model="semantic",
        settings_version="acceptance-v1",
        status="FAILED",
        failure_detail="Optional semantic enrichment failed.",
    )
    session.add(semantic)
    session.flush()
    return document, structural, index


def test_zero_content_student_can_stream_one_safe_tutor_turn_and_hard_safety_blocks_model(
    factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Track A scenarios 1, 2, and protected Safety/model-call invariants."""

    from services.tutor import runtime as tutor_runtime

    monkeypatch.setattr(
        tutor_runtime,
        "get_settings",
        lambda: Settings(_env_file=None, model_provider="mock"),
    )
    client = _student_client(factory, "zero-content")
    try:
        opened = client.post("/api/v1/student/math/session")
        resumed = client.post("/api/v1/student/math/session")
        session_id = opened.json()["id"]
        normal = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "Explain equivalent fractions."},
        )
        blocked = client.post(
            f"/api/v1/student/math/session/{session_id}/turn/stream",
            json={"content": "How can I make a weapon?"},
        )
    finally:
        _clear_overrides()

    assert opened.status_code == resumed.status_code == 200
    assert opened.json()["id"] == resumed.json()["id"]
    assert normal.headers["content-type"].startswith("text/event-stream")
    assert "event: delta" in normal.text and "event: turn" in normal.text
    assert json.loads(normal.text.split("event: turn\ndata: ", 1)[1].split("\n\n", 1)[0])["text"]
    assert "event: delta" not in blocked.text and "event: turn" in blocked.text

    with factory() as session:
        learning_session = session.get(LearningSession, UUID(session_id))
        messages = (
            session.query(LearningMessage)
            .filter_by(session_id=UUID(session_id))
            .order_by(LearningMessage.created_at, LearningMessage.id)
            .all()
        )
        tutor_executions = session.query(AIExecution).filter_by(task="tutor").count()
        student = session.query(Student).join(User).filter(User.external_subject == "zero-content").one()

    assert learning_session is not None and learning_session.status == "OPEN"
    assert learning_session.student_id == student.id
    assert [message.role for message in messages] == ["student", "tutor", "student", "tutor"]
    assert messages[1].payload["source_refs"] == []
    assert tutor_executions == 1


def test_structural_index_grounding_remains_ready_when_semantic_enrichment_fails(
    factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    """Track A scenarios 3 and 4, including structural-only provenance."""

    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="acceptance")
    with factory.begin() as session:
        student = _student(session)
        document, structural, index = _structural_grounding(
            session,
            student=student,
            storage=storage,
        )
        retrieval = RetrievalService(session, embedding_gateway=_embedding_gateway(session)).retrieve(
            student_id=student.id,
            question="Show a decimal example.",
        )
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning_session)
        session.flush()
        context = TutorContextBuilder(
            session,
            retrieval_service=RetrievalService(session, embedding_gateway=_embedding_gateway(session)),
        ).build(
            learning_session=learning_session,
            question="Explain decimal place value.",
        )
        parent_status = parent_content_status_for_student(session, student_id=student.id)

    item = parent_status.documents[0]
    assert structural.status == index.status == "COMPLETED"
    assert index.semantic_processing_run_id is None
    assert item.status == "READY"
    assert item.stages.semantic == "FAILED"
    assert item.stages.index == "READY"
    assert retrieval and any("decimal" in block.text.casefold() for block in retrieval)
    assert all(block.semantic_type is None and block.source_ref.startswith("track-a.md#") for block in retrieval)
    assert all(block.source_refs and block.page_numbers for block in retrieval)
    assert any("decimal" in block.text.casefold() for block in context.retrieval)
    assert document.original_storage_key.startswith(f"content/{student.id}/")


def test_question_driven_intelligence_excludes_school_focus_and_uses_recent_continuity(
    factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    """Track A scenarios 5 through 8 without a curriculum-position authority."""

    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="acceptance")
    with factory.begin() as session:
        student = _student(session)
        _structural_grounding(session, student=student, storage=storage)
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        run = IntelligenceProcessingRun(
            student_id=student.id,
            rubric_version="acceptance-v1",
            policy_version="acceptance-v1",
            status="COMPLETED",
            scope={},
        )
        session.add_all((learning_session, run))
        session.flush()
        session.add(
            LearningMessage(
                session_id=learning_session.id,
                role="tutor",
                content="Equivalent fractions name the same amount.",
                payload={"concept_ref": "equivalent_fractions"},
            )
        )
        active = CurrentLearningState(
            student_id=student.id,
            processing_run_id=run.id,
            subject="MATH",
            state_type="active_difficulty",
            concept_ref="equivalent_fractions",
            detail="Equivalent fractions need one careful comparison.",
            status="ACTIVE",
            evidence_refs=[],
            policy_version=CURRENT_STATE_POLICY_VERSION,
        )
        deprecated = CurrentLearningState(
            student_id=student.id,
            processing_run_id=run.id,
            subject="MATH",
            state_type="current_school_focus",
            concept_ref="geometry",
            detail="Historical school focus: geometry.",
            status="ACTIVE",
            evidence_refs=[],
            policy_version=CURRENT_STATE_POLICY_VERSION,
        )
        excluded = [
            CurrentLearningState(
                student_id=student.id,
                processing_run_id=run.id,
                subject="MATH",
                state_type="active_difficulty",
                concept_ref="geometry",
                detail=f"{status} geometry history.",
                status=status,
                evidence_refs=[],
                policy_version=CURRENT_STATE_POLICY_VERSION,
                expires_at=datetime.now(UTC) - timedelta(seconds=1) if status == "ACTIVE" else None,
            )
            for status in ("RESOLVED", "SUPERSEDED", "ACTIVE")
        ]
        session.add_all((active, deprecated, *excluded))
        builder = TutorContextBuilder(
            session,
            retrieval_service=RetrievalService(session, embedding_gateway=_embedding_gateway(session)),
        )
        fractions = builder.build(
            learning_session=learning_session,
            question="Explain equivalent fractions.",
        )
        continuation = builder.build(learning_session=learning_session, question="Continue.")
        geometry = builder.build(learning_session=learning_session, question="Explain geometry.")
        decimals = builder.build(learning_session=learning_session, question="Explain decimal place value.")

    assert [item.source_id for item in fractions.intelligence] == [active.id]
    assert continuation.focus is not None and continuation.focus.concept_key == "equivalent_fractions"
    assert [item.source_id for item in continuation.intelligence] == [active.id]
    assert geometry.intelligence == ()
    assert decimals.intelligence == ()
    assert any("decimal" in block.text.casefold() for block in decimals.retrieval)
