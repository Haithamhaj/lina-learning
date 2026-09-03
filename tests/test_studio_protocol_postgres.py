"""PostgreSQL contracts for committed Studio feed wake-up notifications."""

from __future__ import annotations

import json
import os
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from services.platform.db.connection import normalize_database_url
from services.platform.db.models import LearningSession, Student, User
from services.studio.contracts import AppendStudioEventCommand, StudioActor
from services.studio.feed import StudioEventFeed
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import StudioStateService


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Studio protocol contracts",
)


def test_studio_event_notifies_only_after_outer_transaction_commits() -> None:
    """A notification is a committed routing hint, never an uncommitted event claim."""

    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(normalize_database_url(database_url))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE studio_canvas_specialist_runs, studio_tutor_observations, "
                "studio_student_interactions, studio_events, studio_snapshots, studio_scenes, "
                "studio_runtimes, learning_messages, learning_segments, learning_sessions, students, users CASCADE"
            )
        )

    with Session(engine) as session:
        user = User(identity_provider="fixture", external_subject=f"protocol-{uuid4().hex}", role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id, display_name="Protocol fixture")
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(
            student_id=student.id,
            learning_session_id=learning_session.id,
        )
        runtime_id = runtime.id
        student_id = student.id
        learning_session_id = learning_session.id
        session.commit()

    listener_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(listener_url, autocommit=True) as listener:
        listener.execute("LISTEN lina_studio_events_v1")
        with Session(engine) as session:
            result = StudioStateService(session).append_event(
                AppendStudioEventCommand(
                    runtime_id=runtime_id,
                    student_id=student_id,
                    learning_session_id=learning_session_id,
                    event_kind="studio.runtime.initialized",
                    event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                    actor=StudioActor.SYSTEM,
                    payload_schema_version="studio-runtime-initialized-v1",
                    payload={},
                    idempotency_key="protocol-notify-1",
                )
            )
            event_sequence = result.event.sequence
            assert list(listener.notifies(timeout=0.05, stop_after=1)) == []
            session.commit()
        notifications = list(listener.notifies(timeout=2, stop_after=1))

    assert len(notifications) == 1
    assert json.loads(notifications[0].payload) == {
        "runtime_id": str(runtime_id),
        "sequence": event_sequence,
    }
    engine.dispose()


def test_feed_listens_before_snapshot_and_replays_committed_event_log() -> None:
    """No-cursor startup sends a Snapshot, then a committed notification wakes log replay."""

    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(normalize_database_url(database_url))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE studio_canvas_specialist_runs, studio_tutor_observations, "
                "studio_student_interactions, studio_events, studio_snapshots, studio_scenes, "
                "studio_runtimes, learning_messages, learning_segments, learning_sessions, students, users CASCADE"
            )
        )
    with Session(engine) as session:
        user = User(identity_provider="fixture", external_subject=f"feed-{uuid4().hex}", role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id, display_name="Feed fixture")
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        runtime_id, student_id, learning_session_id = runtime.id, student.id, learning_session.id
        session.commit()

    listener_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    feed = StudioEventFeed(
        session_factory=lambda: Session(engine),
        listener_factory=lambda: psycopg.connect(listener_url, autocommit=True),
        heartbeat_seconds=1,
    )
    stream = feed.stream(student_id=student_id, runtime_id=runtime_id, after_sequence=None)
    try:
        initial = next(stream)
        assert "STUDIO_SNAPSHOT" in initial
        with Session(engine) as session:
            StudioStateService(session).append_event(
                AppendStudioEventCommand(
                    runtime_id=runtime_id,
                    student_id=student_id,
                    learning_session_id=learning_session_id,
                    event_kind="studio.runtime.initialized",
                    event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                    actor=StudioActor.SYSTEM,
                    payload_schema_version="studio-runtime-initialized-v1",
                    payload={},
                    idempotency_key="feed-live-1",
                )
            )
            session.commit()
        assert '"sequence":1' in next(stream)
    finally:
        stream.close()
        engine.dispose()
