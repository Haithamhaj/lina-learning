from __future__ import annotations

import importlib
from io import BytesIO
import os
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.platform.db.models import LearningMessage, LearningSession, Student, StudentSourceAsset, User
from services.platform.storage import LocalObjectStorage
from services.student_sources.validation import validate_student_source


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Student source tests",
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
    user = User(identity_provider="clerk", external_subject=subject, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name=subject)
    session.add(student)
    session.flush()
    return student


def _source_service():
    try:
        module = importlib.import_module("services.student_sources.service")
    except ModuleNotFoundError:
        module = None
    assert module is not None
    return module


def _pdf() -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 32), "white").save(output, format="PDF")
    return output.getvalue()


def test_source_original_is_immutable_and_exactly_linked_to_student_message(
    postgres_session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    service = _source_service()
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    original = _pdf()
    source = validate_student_source(
        content=original, filename="lesson.pdf", content_type="application/pdf"
    )

    with postgres_session_factory.begin() as session:
        student = _student(session, "source-owner")
        learning = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning)
        session.flush()
        message = LearningMessage(session_id=learning.id, role="student", content="What is here?")
        session.add(message)
        session.flush()
        asset = service.store_source_asset(
            session,
            storage=storage,
            student_id=student.id,
            learning_session=learning,
            source_message=message,
            source=source,
        )
        asset_id = asset.id
        key = asset.storage_key
        assert message.source_asset_id == asset.id

    stored = storage.get(key)
    assert stored.content == original
    assert stored.metadata.checksum_sha256 == source.checksum_sha256
    with pytest.raises(Exception):
        storage.put(key, b"replacement")

    with postgres_session_factory() as session:
        asset = session.get(StudentSourceAsset, asset_id)
        assert asset is not None
        assert asset.source_message_id == message.id
        assert asset.storage_key == key
        assert asset.checksum_sha256 == source.checksum_sha256


def test_owned_source_lookup_denies_cross_student_and_cross_session(
    postgres_session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    service = _source_service()
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    source = validate_student_source(
        content=_pdf(),
        filename="lesson.pdf",
        content_type="application/pdf",
    )
    with postgres_session_factory.begin() as session:
        owner = _student(session, "owner")
        other = _student(session, "other")
        owner_session = LearningSession(student_id=owner.id, subject="MATH")
        other_session = LearningSession(student_id=owner.id, subject="MATH")
        session.add_all([owner_session, other_session])
        session.flush()
        message = LearningMessage(session_id=owner_session.id, role="student", content="Help")
        session.add(message)
        session.flush()
        asset = service.store_source_asset(
            session,
            storage=storage,
            student_id=owner.id,
            learning_session=owner_session,
            source_message=message,
            source=source,
        )

        assert service.owned_source_asset(
            session, student_id=owner.id, learning_session_id=owner_session.id, asset_id=asset.id
        ) is asset
        assert service.owned_source_asset(
            session, student_id=other.id, learning_session_id=owner_session.id, asset_id=asset.id
        ) is None
        assert service.owned_source_asset(
            session, student_id=owner.id, learning_session_id=other_session.id, asset_id=asset.id
        ) is None
        assert service.owned_source_asset(
            session, student_id=owner.id, learning_session_id=owner_session.id, asset_id=uuid4()
        ) is None


def test_followup_links_latest_owned_source_without_duplicate_asset(
    postgres_session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    service = _source_service()
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    source = validate_student_source(
        content=_pdf(),
        filename="lesson.pdf",
        content_type="application/pdf",
    )
    with postgres_session_factory.begin() as session:
        student = _student(session, "followup-owner")
        learning = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning)
        session.flush()
        first = LearningMessage(session_id=learning.id, role="student", content="Help")
        session.add(first)
        session.flush()
        asset = service.store_source_asset(
            session,
            storage=storage,
            student_id=student.id,
            learning_session=learning,
            source_message=first,
            source=source,
        )
        followup = LearningMessage(session_id=learning.id, role="student", content="Why?")
        session.add(followup)
        session.flush()
        service.link_source_to_message(followup, asset=asset)
        session.flush()

        assert followup.source_asset_id == asset.id
        assert session.query(StudentSourceAsset).count() == 1
        provider_input = service.provider_source_input(storage=storage, asset=asset)
        assert provider_input == {
            "kind": "PDF",
            "filename": "lesson.pdf",
            "content_type": "application/pdf",
            "content": source.content,
        }


def test_database_failure_compensates_by_deleting_the_stored_original(tmp_path: Path) -> None:
    service = _source_service()
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    source = validate_student_source(
        content=_pdf(),
        filename="lesson.pdf",
        content_type="application/pdf",
    )
    student_id = uuid4()
    learning = LearningSession(id=uuid4(), student_id=student_id, subject="MATH")
    message = LearningMessage(id=uuid4(), session_id=learning.id, role="student", content="Help")

    class _FailingDatabase:
        def add(self, _: object) -> None:
            return None

        def flush(self, _: object) -> None:
            raise RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.store_source_asset(
            _FailingDatabase(),
            storage=storage,
            student_id=student_id,
            learning_session=learning,
            source_message=message,
            source=source,
        )
    expected_key_prefix = f"student-sources/{student_id}/{learning.id}/"
    assert not any(path.is_file() for path in (tmp_path / "objects" / expected_key_prefix).glob("**/*"))
