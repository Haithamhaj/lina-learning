"""Read-only Canvas composition state contracts."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db import models as m
from services.platform.db.connection import normalize_database_url


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Canvas composition status contracts",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE jobs, studio_canvas_specialist_runs, studio_scenes, "
                "studio_snapshots, studio_runtimes, learning_messages, "
                "learning_sessions, students, users CASCADE"
            )
        )
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _run_lineage(session: Session) -> tuple[m.Student, m.StudioRuntime, m.LearningMessage]:
    user = m.User(identity_provider="composition-status", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = m.Student(user_id=user.id, display_name="Composition fixture")
    session.add(student)
    session.flush()
    learning = m.LearningSession(student_id=student.id, subject="MATH", status="OPEN")
    session.add(learning)
    session.flush()
    runtime = m.StudioRuntime(student_id=student.id, learning_session_id=learning.id)
    session.add(runtime)
    session.flush()
    message = m.LearningMessage(
        session_id=learning.id,
        role="tutor",
        content="I will prepare a visual.",
        payload={
            "agentic_canvas": {
                "status": "ADMITTED",
                "brief": {"objective": "Compare two decimal positions."},
            }
        },
        created_at=datetime.now(UTC),
    )
    session.add(message)
    session.flush()
    return student, runtime, message


def test_current_agentic_run_projects_owned_pending_objective_without_writes(
    factory: sessionmaker[Session],
) -> None:
    """Catches falling back to legacy visual status instead of the admitted Run."""

    from services.studio.composition_status import load_canvas_composition_view

    with factory.begin() as session:
        student, runtime, message = _run_lineage(session)
        run = m.StudioCanvasSpecialistRun(
            studio_runtime_id=runtime.id,
            student_id=student.id,
            learning_session_id=runtime.learning_session_id,
            source_message_id=message.id,
            scene_id=None,
            base_scene_id=None,
            base_scene_version=0,
            subject_key="MATH",
            capability_profile_version="agentic-canvas-v1",
            status="PENDING",
            output_schema_version="agentic-canvas-scene-v3",
        )
        session.add(run)
        session.flush()
        before = session.execute(text("SELECT count(*) FROM studio_canvas_specialist_runs")).scalar_one()
        view = load_canvas_composition_view(session, student_id=student.id, runtime_id=runtime.id)
        after = session.execute(text("SELECT count(*) FROM studio_canvas_specialist_runs")).scalar_one()

    assert before == after == 1
    assert view.runtime_id == runtime.id
    assert view.run_id == run.id
    assert view.run_status == "PENDING"
    assert view.objective == "Compare two decimal positions."
    assert view.scene_id is None
    assert view.scene_ready is False
