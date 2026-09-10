from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from apps.api.routes.studio import get_studio_object_storage
from services.platform.auth import AuthenticatedPrincipal, UserRole
from services.platform.auth.clerk import get_current_principal
from services.platform.db import models as m
from services.platform.db.connection import normalize_database_url
from services.platform.db.session import get_session
from services.platform.storage import LocalObjectStorage
from services.studio.generated_assets import (
    adopt_generated_image,
    owned_generated_asset,
)
from services.studio.service import StudioStateService

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Disposable PostgreSQL DATABASE_URL is required for generated Studio asset contracts",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE studio_generated_assets, studio_canvas_specialist_runs, "
                "studio_tutor_observations, studio_student_interactions, studio_events, "
                "studio_snapshots, studio_scenes, studio_runtimes, learning_messages, "
                "learning_segments, learning_sessions, students, users CASCADE"
            )
        )
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (2, 2), color="white").save(output, format="PNG")
    return output.getvalue()


def _student(session: Session, subject: str) -> m.Student:
    user = m.User(identity_provider="clerk", external_subject=subject, role="STUDENT")
    session.add(user)
    session.flush()
    student = m.Student(user_id=user.id, display_name=subject)
    session.add(student)
    session.flush()
    return student


def _run(session: Session, *, student: m.Student) -> tuple[m.StudioRuntime, m.StudioCanvasSpecialistRun]:
    learning = m.LearningSession(student_id=student.id, subject="SCIENCE")
    session.add(learning)
    session.flush()
    message = m.LearningMessage(session_id=learning.id, role="tutor", content="Observe this")
    session.add(message)
    session.flush()
    runtime = StudioStateService(session).get_or_create_runtime(
        student_id=student.id,
        learning_session_id=learning.id,
    )
    run = m.StudioCanvasSpecialistRun(
        studio_runtime_id=runtime.id,
        student_id=student.id,
        learning_session_id=learning.id,
        source_message_id=message.id,
        base_scene_version=0,
        subject_key="CANVAS",
        capability_profile_version="agentic-canvas-v1",
        output_schema_version="agentic-canvas-scene-v1",
    )
    session.add(run)
    session.flush()
    return runtime, run


def test_generated_asset_is_visible_only_inside_exact_student_runtime(
    postgres_session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    with postgres_session_factory.begin() as session:
        owner = _student(session, "generated-owner")
        other = _student(session, "generated-other")
        runtime, run = _run(session, student=owner)
        asset = adopt_generated_image(
            session,
            storage=storage,
            run=run,
            temporary_handle="hosted-image-1",
            content=_png(),
            content_type="image/png",
        ).asset
        assert owned_generated_asset(
            session,
            student_id=owner.id,
            runtime_id=runtime.id,
            asset_id=asset.id,
        ) is asset
        assert owned_generated_asset(
            session,
            student_id=other.id,
            runtime_id=runtime.id,
            asset_id=asset.id,
        ) is None
        assert owned_generated_asset(
            session,
            student_id=owner.id,
            runtime_id=uuid4(),
            asset_id=asset.id,
        ) is None


def test_authenticated_private_read_never_exposes_provider_location(
    postgres_session_factory: sessionmaker[Session], tmp_path: Path
) -> None:
    from apps.api.main import app

    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    with postgres_session_factory.begin() as session:
        owner = _student(session, "asset-api-owner")
        runtime, run = _run(session, student=owner)
        asset = adopt_generated_image(
            session,
            storage=storage,
            run=run,
            temporary_handle="hosted-image-api",
            content=_png(),
            content_type="image/png",
        ).asset
        runtime_id, asset_id = runtime.id, asset.id

    def database_session():
        with postgres_session_factory.begin() as session:
            yield session

    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject="asset-api-owner",
        role=UserRole.STUDENT,
    )
    app.dependency_overrides[get_studio_object_storage] = lambda: storage
    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/student/studio/{runtime_id}/assets/{asset_id}")
            assert response.status_code == 200
            assert response.content == _png()
            assert response.headers["content-type"] == "image/png"
            assert response.headers["cache-control"] == "private, no-store"
            assert "url" not in response.headers

            app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
                subject="asset-api-other",
                role=UserRole.STUDENT,
            )
            assert client.get(f"/api/v1/student/studio/{runtime_id}/assets/{asset_id}").status_code == 404
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_principal, None)
        app.dependency_overrides.pop(get_studio_object_storage, None)
