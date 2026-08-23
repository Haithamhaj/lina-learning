"""Fixture upload and Docling adapter tests without a real school book."""

from base64 import b64encode
from pathlib import Path
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.content.ingestion import ingest_source_document
from services.content.docling_adapter import extract_structural_markdown
from services.content.processing import process_markdown_document, process_structural_document
from services.content.structural_contract import NormalizedStructuralItem
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import AIExecution, ContentDocument, ContentIndexRun, DocumentStructuralItem, IndexedContentBlock, IndexedContentBlockSource, Job, JobStatus, ModelTask, Student, User
from services.platform.jobs import enqueue_job
from services.platform.storage import LocalObjectStorage
from workers.content_handlers import STRUCTURAL_PROCESSING_JOB, register_content_handlers
from workers.job_worker import JobHandlerRegistry, run_once
from services.retrieval.service import RetrievalService


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for content ingestion tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE jobs, indexed_content_block_sources, indexed_content_blocks, content_index_runs, content_semantic_item_sources, content_semantic_items, content_semantic_processing_runs, document_structural_items, content_blocks, curriculum_nodes, content_processing_runs, content_documents CASCADE"))
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def make_student(session: Session) -> object:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Lina fixture")
    session.add(student)
    session.flush()
    return student.id


def embedding_gateway(session: Session) -> ModelGateway:
    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            return ModelResult(output={"embeddings": [[0.01] * 1536 for _ in payload["input"]]})

    return ModelGateway(
        session,
        routes={ModelTask.EMBEDDING: ModelRoute("fixture", "text-embedding-3-small")},
        providers={"fixture": Provider()},
    )


def failing_embedding_gateway(session: Session) -> ModelGateway:
    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            return ModelResult(output={"embeddings": [[0.01] * 8 for _ in payload["input"]]})

    return ModelGateway(
        session,
        routes={ModelTask.EMBEDDING: ModelRoute("fixture", "text-embedding-3-small")},
        providers={"fixture": Provider()},
    )


def test_fixture_upload_preserves_original_and_rejects_duplicate_checksum(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    source = b"# Equivalent Fractions\n\n1/2 = 2/4"
    with postgres_session_factory.begin() as session:
        student_id = make_student(session)
        first = ingest_source_document(
            session,
            storage=storage,
            student_id=student_id,
            grade_level=5,
            subject="MATH",
            filename="fractions.md",
            content_type="text/markdown",
            content=source,
        )
        duplicate = ingest_source_document(
            session,
            storage=storage,
            student_id=student_id,
            grade_level=5,
            subject="MATH",
            filename="renamed-fractions.md",
            content_type="text/markdown",
            content=source,
        )

    assert storage.get(first.original_storage_key).content.startswith(b"# Equivalent")
    assert duplicate.id == first.id
    with postgres_session_factory() as session:
        assert session.get(ContentDocument, first.id).original_checksum == storage.head(first.original_storage_key).checksum_sha256
        assert session.query(ContentDocument).count() == 1


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "message"),
    [
        ("notes.txt", "text/plain", b"not a supported source", "Only Markdown"),
        ("book.pdf", "application/pdf", b"not a PDF", "PDF source must"),
        ("book.md", "application/pdf", b"%PDF-1.7\n", "filename must"),
    ],
)
def test_upload_rejects_invalid_or_mismatched_source_files(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    filename: str,
    content_type: str,
    content: bytes,
    message: str,
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    with postgres_session_factory.begin() as session:
        with pytest.raises(ValueError, match=message):
            ingest_source_document(
                session,
                storage=storage,
                student_id=make_student(session),
                grade_level=5,
                subject="MATH",
                filename=filename,
                content_type=content_type,
                content=content,
            )


def test_docling_normalizes_a_markdown_fixture_with_source_text() -> None:
    markdown = extract_structural_markdown(
        "# Equivalent Fractions\n\nOne half is equal to two fourths."
    )

    assert "Equivalent Fractions" in markdown
    assert "two fourths" in markdown


def test_processing_persists_a_versioned_source_linked_structural_block(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    with postgres_session_factory.begin() as session:
        document = ingest_source_document(
            session, storage=storage, student_id=make_student(session), grade_level=5,
            subject="MATH", filename="fractions.md", content_type="text/markdown",
            content=b"# Equivalent Fractions\n\nOne half is equal to two fourths.",
        )
        run = process_markdown_document(session, storage=storage, document=document)

    assert run.status == "COMPLETED"
    assert run.processor_version.startswith("docling-")


def test_structural_processing_is_idempotent_and_preserves_item_provenance(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    monkeypatch.setattr(
        "services.content.processing.extract_structural_items",
        lambda **_: [
            NormalizedStructuralItem(
                item_key="#/texts/4",
                parent_item_key=None,
                sibling_order=0,
                reading_order=0,
                hierarchy_depth=0,
                item_type="list_item",
                text="Use place value to multiply by 10.",
                caption_text=None,
                caption_item_keys=(),
                heading_level=None,
                page_number=2,
                source_ref="book.pdf#page=2:item=4",
                provenance={"locations": [{"page_no": 2}]},
                attributes={"docling_label": "list_item"},
            )
        ],
    )
    with postgres_session_factory.begin() as session:
        document = ingest_source_document(
            session, storage=storage, student_id=make_student(session), grade_level=5,
            subject="MATH", filename="book.pdf", content_type="application/pdf",
            content=b"%PDF-1.7\nfixture",
        )
        first = process_structural_document(session, storage=storage, document=document)
        second = process_structural_document(session, storage=storage, document=document)
        items = session.query(DocumentStructuralItem).filter_by(processing_run_id=first.id).all()

    assert first.id == second.id
    assert first.status == "COMPLETED"
    assert len(items) == 1
    assert items[0].page_number == 2
    assert items[0].source_ref == "book.pdf#page=2:item=4"
    assert items[0].attributes["docling_label"] == "list_item"


def test_structural_processing_can_run_through_the_durable_worker(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    with postgres_session_factory.begin() as session:
        document = ingest_source_document(
            session, storage=storage, student_id=make_student(session), grade_level=5,
            subject="MATH", filename="fractions.md", content_type="text/markdown",
            content=b"# Equivalent Fractions\n\nOne half is equal to two fourths.",
        )
        enqueue_job(
            session,
            job_type=STRUCTURAL_PROCESSING_JOB,
            payload={"document_id": str(document.id)},
            idempotency_key=f"structural:{document.id}:docling-2.121.0",
        )

    registry = JobHandlerRegistry()
    register_content_handlers(
        registry,
        session_factory=postgres_session_factory,
        storage=storage,
    )
    assert run_once(postgres_session_factory, registry, worker_id="content-test") == "COMPLETED"

    with postgres_session_factory() as session:
        assert session.query(DocumentStructuralItem).filter_by(document_id=document.id).count() > 0


def test_completed_structural_job_queues_one_structural_index_job(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    with postgres_session_factory.begin() as session:
        document = ingest_source_document(
            session, storage=storage, student_id=make_student(session), grade_level=5,
            subject="MATH", filename="fractions.md", content_type="text/markdown",
            content=b"# Equivalent Fractions\n\nOne half is equal to two fourths.",
        )
        enqueue_job(
            session,
            job_type=STRUCTURAL_PROCESSING_JOB,
            payload={"document_id": str(document.id)},
            idempotency_key=f"content-structural-process:{document.id}:docling-2.121.0",
        )

    registry = JobHandlerRegistry()
    register_content_handlers(registry, session_factory=postgres_session_factory, storage=storage)
    assert run_once(postgres_session_factory, registry, worker_id="content-test") == "COMPLETED"

    with postgres_session_factory() as session:
        index_jobs = session.query(Job).filter_by(job_type="content.structural_index").all()
        assert len(index_jobs) == 1
        assert index_jobs[0].payload["document_id"] == str(document.id)
        assert index_jobs[0].status == "PENDING"


def test_structural_index_job_builds_structural_blocks_with_gateway_lineage(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    monkeypatch.setattr("workers.content_handlers.create_embedding_gateway", embedding_gateway, raising=False)
    with postgres_session_factory.begin() as session:
        document = ingest_source_document(
            session, storage=storage, student_id=make_student(session), grade_level=5,
            subject="MATH", filename="fractions.md", content_type="text/markdown",
            content=b"# Equivalent Fractions\n\nOne half is equal to two fourths.",
        )
        enqueue_job(
            session,
            job_type=STRUCTURAL_PROCESSING_JOB,
            payload={"document_id": str(document.id)},
            idempotency_key=f"content-structural-process:{document.id}:docling-2.121.0",
        )

    registry = JobHandlerRegistry()
    register_content_handlers(registry, session_factory=postgres_session_factory, storage=storage)
    assert run_once(postgres_session_factory, registry, worker_id="content-test") == "COMPLETED"
    assert run_once(postgres_session_factory, registry, worker_id="content-test") == "COMPLETED"

    with postgres_session_factory() as session:
        index_run = session.query(ContentIndexRun).one()
        block = session.query(IndexedContentBlock).filter_by(index_run_id=index_run.id).first()
        source = session.query(IndexedContentBlockSource).filter_by(block_id=block.id).one()
        structural_item = session.get(DocumentStructuralItem, source.structural_item_id)
        execution = session.query(AIExecution).filter_by(content_index_run_id=index_run.id).one()
        retrieved = RetrievalService(session, embedding_gateway=embedding_gateway(session)).retrieve(
            student_id=document.student_id,
            question="What are equivalent fractions?",
        )

    assert index_run.status == "COMPLETED" and index_run.semantic_processing_run_id is None
    assert block is not None and block.semantic_item_id is None
    assert source.semantic_item_id is None and source.source_ref == structural_item.source_ref
    assert execution.document_id == document.id and execution.semantic_processing_run_id is None
    assert retrieved and retrieved[0].source_ref == source.source_ref


def test_failed_structural_index_run_returns_job_to_retry_without_losing_structure(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    monkeypatch.setattr("workers.content_handlers.create_embedding_gateway", failing_embedding_gateway, raising=False)
    with postgres_session_factory.begin() as session:
        document = ingest_source_document(
            session, storage=storage, student_id=make_student(session), grade_level=5,
            subject="MATH", filename="fractions.md", content_type="text/markdown",
            content=b"# Equivalent Fractions\n\nOne half is equal to two fourths.",
        )
        enqueue_job(
            session,
            job_type=STRUCTURAL_PROCESSING_JOB,
            payload={"document_id": str(document.id)},
            idempotency_key=f"content-structural-process:{document.id}:docling-2.121.0",
        )

    registry = JobHandlerRegistry()
    register_content_handlers(registry, session_factory=postgres_session_factory, storage=storage)
    assert run_once(postgres_session_factory, registry, worker_id="content-test") == JobStatus.COMPLETED
    assert run_once(postgres_session_factory, registry, worker_id="content-test") == JobStatus.PENDING

    with postgres_session_factory() as session:
        index_run = session.query(ContentIndexRun).one()
        index_job = session.query(Job).filter_by(job_type="content.structural_index").one()
        structural_items = session.query(DocumentStructuralItem).filter_by(document_id=document.id).count()

    assert index_run.status == "FAILED" and index_run.semantic_processing_run_id is None
    assert index_job.status == JobStatus.PENDING and index_job.attempt_count == 1
    assert structural_items > 0


def test_failed_structural_job_does_not_queue_an_index_job(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    monkeypatch.setattr(
        "services.content.processing.extract_structural_items",
        lambda **_: (_ for _ in ()).throw(ValueError("fixture structural failure")),
    )
    with postgres_session_factory.begin() as session:
        document = ingest_source_document(
            session, storage=storage, student_id=make_student(session), grade_level=5,
            subject="MATH", filename="fractions.md", content_type="text/markdown",
            content=b"# Equivalent Fractions\n\nOne half is equal to two fourths.",
        )
        enqueue_job(
            session,
            job_type=STRUCTURAL_PROCESSING_JOB,
            payload={"document_id": str(document.id)},
            idempotency_key=f"content-structural-process:{document.id}:docling-2.121.0",
        )

    registry = JobHandlerRegistry()
    register_content_handlers(registry, session_factory=postgres_session_factory, storage=storage)
    assert run_once(postgres_session_factory, registry, worker_id="content-test") == JobStatus.PENDING

    with postgres_session_factory() as session:
        assert session.query(Job).filter_by(job_type="content.structural_index").count() == 0


def test_failed_reprocess_index_preserves_the_previous_completed_index(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    with postgres_session_factory.begin() as session:
        document = ingest_source_document(
            session, storage=storage, student_id=make_student(session), grade_level=5,
            subject="MATH", filename="fractions.md", content_type="text/markdown",
            content=b"# Equivalent Fractions\n\nOne half is equal to two fourths.",
        )
        enqueue_job(
            session,
            job_type=STRUCTURAL_PROCESSING_JOB,
            payload={"document_id": str(document.id), "processor_version": "fixture-v1"},
            idempotency_key=f"content-structural-process:{document.id}:fixture-v1",
        )

    registry = JobHandlerRegistry()
    monkeypatch.setattr("workers.content_handlers.create_embedding_gateway", embedding_gateway, raising=False)
    register_content_handlers(registry, session_factory=postgres_session_factory, storage=storage)
    assert run_once(postgres_session_factory, registry, worker_id="content-test") == JobStatus.COMPLETED
    assert run_once(postgres_session_factory, registry, worker_id="content-test") == JobStatus.COMPLETED

    with postgres_session_factory.begin() as session:
        previous = session.query(ContentIndexRun).filter_by(status="COMPLETED").one()
        previous_block_count = session.query(IndexedContentBlock).filter_by(index_run_id=previous.id).count()
        enqueue_job(
            session,
            job_type=STRUCTURAL_PROCESSING_JOB,
            payload={"document_id": str(document.id), "processor_version": "fixture-v2"},
            idempotency_key=f"content-structural-process:{document.id}:fixture-v2",
        )

    failed_registry = JobHandlerRegistry()
    monkeypatch.setattr("workers.content_handlers.create_embedding_gateway", failing_embedding_gateway, raising=False)
    register_content_handlers(failed_registry, session_factory=postgres_session_factory, storage=storage)
    assert run_once(postgres_session_factory, failed_registry, worker_id="content-test") == JobStatus.COMPLETED
    assert run_once(postgres_session_factory, failed_registry, worker_id="content-test") == JobStatus.PENDING

    with postgres_session_factory() as session:
        replacement = session.query(ContentIndexRun).filter_by(status="FAILED").one()
        retained_blocks = session.query(IndexedContentBlock).filter_by(index_run_id=previous.id).count()

    assert replacement.structural_processing_run_id != previous.structural_processing_run_id
    assert retained_blocks == previous_block_count > 0


def test_parent_upload_endpoint_requires_parent_role(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    from apps.api.main import app
    from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
    from services.platform.db.session import get_session

    with postgres_session_factory.begin() as session:
        student_id = make_student(session)

    app.dependency_overrides[get_session] = lambda: postgres_session_factory()
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject="student-fixture", role=UserRole.STUDENT
    )
    try:
        response = TestClient(app).post(
            "/api/v1/content/documents",
            json={
                "student_id": str(student_id), "grade_level": 5, "subject": "MATH",
                "filename": "fractions.md", "content_type": "text/markdown",
                "content_base64": "IyBGcmFjdGlvbnM=",
            },
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_principal, None)


def test_parent_upload_queues_one_structural_job_for_duplicate_source(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.api.main import app
    from apps.api.routes import content as content_routes
    from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
    from services.platform.db.session import get_session

    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    with postgres_session_factory.begin() as session:
        student_id = make_student(session)

    def request_session():
        with postgres_session_factory.begin() as session:
            yield session

    monkeypatch.setattr(content_routes, "create_object_storage", lambda _: storage)
    app.dependency_overrides[get_session] = request_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject="parent-fixture", role=UserRole.PARENT_ADMIN
    )
    try:
        payload = {
            "student_id": str(student_id),
            "grade_level": 5,
            "subject": "MATH",
            "filename": "fractions.md",
            "content_type": "text/markdown",
            "content_base64": b64encode(b"# Fractions\n\nOne half equals two fourths.").decode(),
        }
        first = TestClient(app).post("/api/v1/content/documents", json=payload)
        second = TestClient(app).post("/api/v1/content/documents", json=payload)
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_principal, None)

    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["document_id"] == second.json()["document_id"]
    with postgres_session_factory() as session:
        jobs = session.query(Job).filter_by(job_type=STRUCTURAL_PROCESSING_JOB).all()
        assert len(jobs) == 1
        assert jobs[0].payload == {
            "document_id": first.json()["document_id"],
            "processor_version": "docling-2.121.0",
        }


def test_reprocess_uses_the_same_structural_to_index_lifecycle(
    tmp_path: Path,
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.api.main import app
    from apps.api.routes import content as content_routes
    from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
    from services.platform.db.session import get_session

    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    monkeypatch.setattr(content_routes, "create_object_storage", lambda _: storage)
    monkeypatch.setattr("workers.content_handlers.create_embedding_gateway", embedding_gateway, raising=False)
    with postgres_session_factory.begin() as session:
        document = ingest_source_document(
            session, storage=storage, student_id=make_student(session), grade_level=5,
            subject="MATH", filename="fractions.md", content_type="text/markdown",
            content=b"# Equivalent Fractions\n\nOne half is equal to two fourths.",
        )

    def request_session():
        with postgres_session_factory.begin() as session:
            yield session

    app.dependency_overrides[get_session] = request_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject="parent-fixture", role=UserRole.PARENT_ADMIN
    )
    try:
        response = TestClient(app).post(f"/api/v1/content/documents/{document.id}/reprocess")
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_principal, None)

    assert response.status_code == 202
    with postgres_session_factory() as session:
        job = session.get(Job, response.json()["job_id"])
        assert job is not None
        assert job.idempotency_key == (
            f"content-structural-process:{document.id}:{response.json()['processor_version']}"
        )

    registry = JobHandlerRegistry()
    register_content_handlers(registry, session_factory=postgres_session_factory, storage=storage)
    assert run_once(postgres_session_factory, registry, worker_id="content-test") == JobStatus.COMPLETED
    assert run_once(postgres_session_factory, registry, worker_id="content-test") == JobStatus.COMPLETED

    with postgres_session_factory() as session:
        job = session.get(Job, response.json()["job_id"])
        index_run = session.query(ContentIndexRun).one()
        assert job is not None and job.result is not None
        assert str(index_run.structural_processing_run_id) == job.result["processing_run_id"]
        assert index_run.semantic_processing_run_id is None
