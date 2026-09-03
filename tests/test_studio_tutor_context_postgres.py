"""PostgreSQL selection contracts for STUDIO-RUNTIME-01."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from services.platform.db.connection import normalize_database_url
from services.platform.db.models import AIExecution, LearningMessage, LearningSession, ModelTask, StudioRuntime, StudioTutorObservation, Student, User
from services.studio.contracts import AppendStudioEventCommand, CreateTutorObservationCommand, StudioActor
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import StudioStateService
from services.studio.tutor_context import StudioTutorWorkspaceContext
from services.tutor.context import TutorContextBuilder


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Studio Tutor context contracts",
)


def test_selection_captures_snapshot_and_contiguous_unseen_events() -> None:
    """A short selection transaction captures one exact observation range."""

    from services.studio.tutor_context import select_studio_tutor_context  # noqa: PLC0415 - RED contract

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE studio_canvas_specialist_runs, studio_tutor_observations, "
                "studio_student_interactions, studio_events, studio_snapshots, studio_scenes, "
                "studio_runtimes, learning_messages, learning_segments, learning_sessions, students, users CASCADE"
            )
        )
    with Session(engine) as session:
        user = User(identity_provider="fixture", external_subject=f"runtime-context-{uuid4().hex}", role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(
            student_id=student.id,
            learning_session_id=learning_session.id,
        )
        for sequence in (1, 2):
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
                    idempotency_key=f"runtime-context-{sequence}",
                )
            )
        student_id, learning_session_id = student.id, learning_session.id
        session.commit()

    selection = select_studio_tutor_context(
        bind=engine,
        student_id=student_id,
        learning_session_id=learning_session_id,
    )

    assert selection is not None
    assert selection.previous_watermark == 0
    assert selection.context.through_sequence == 2
    assert selection.context.snapshot_sequence == 2
    assert [event.sequence for event in selection.context.unseen_events] == [1, 2]
    assert selection.context.observation_id is not None
    assert select_studio_tutor_context(
        bind=engine,
        student_id=uuid4(),
        learning_session_id=learning_session_id,
    ) is None
    engine.dispose()


def test_selection_without_runtime_is_a_noop_and_active_runtime_without_events_keeps_snapshot() -> None:
    """Chat never creates a Runtime, while an idle Runtime still supplies its Snapshot."""

    from services.studio.tutor_context import select_studio_tutor_context  # noqa: PLC0415 - RED contract

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE studio_tutor_observations, studio_events, studio_snapshots, studio_runtimes, learning_sessions, students, users CASCADE"))
    with Session(engine) as session:
        user = User(identity_provider="fixture", external_subject=f"runtime-idle-{uuid4().hex}", role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        student_id, learning_session_id = student.id, learning_session.id
        session.commit()

    assert select_studio_tutor_context(bind=engine, student_id=student_id, learning_session_id=learning_session_id) is None

    with Session(engine) as session:
        StudioStateService(session).get_or_create_runtime(student_id=student_id, learning_session_id=learning_session_id)
        session.commit()
    selection = select_studio_tutor_context(bind=engine, student_id=student_id, learning_session_id=learning_session_id)
    assert selection is not None
    assert selection.context.snapshot_sequence == 0
    assert selection.context.unseen_events == ()
    assert selection.context.observation_id is None
    with Session(engine) as session:
        assert session.scalar(text("SELECT count(*) FROM studio_tutor_observations")) == 0
    engine.dispose()


def test_acknowledgement_commits_exact_selected_range_without_skipping_newer_events() -> None:
    """A completed Tutor turn advances only the observation's captured boundary."""

    from services.studio.tutor_context import (  # noqa: PLC0415 - RED contract
        acknowledge_studio_tutor_observation,
        select_studio_tutor_context,
    )

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE studio_canvas_specialist_runs, studio_tutor_observations, "
                "studio_student_interactions, studio_events, studio_snapshots, studio_scenes, "
                "studio_runtimes, learning_messages, learning_segments, learning_sessions, students, users CASCADE"
            )
        )
    with Session(engine) as session:
        user = User(identity_provider="fixture", external_subject=f"runtime-ack-{uuid4().hex}", role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        StudioStateService(session).append_event(
            AppendStudioEventCommand(
                runtime_id=runtime.id, student_id=student.id, learning_session_id=learning_session.id,
                event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                actor=StudioActor.SYSTEM, payload_schema_version="studio-runtime-initialized-v1", payload={}, idempotency_key="runtime-ack-1",
            )
        )
        runtime_id, student_id, learning_session_id = runtime.id, student.id, learning_session.id
        session.commit()
    selection = select_studio_tutor_context(bind=engine, student_id=student_id, learning_session_id=learning_session_id)
    assert selection is not None and selection.context.observation_id is not None
    with Session(engine) as session:
        StudioStateService(session).append_event(
            AppendStudioEventCommand(
                runtime_id=runtime_id, student_id=student_id, learning_session_id=learning_session_id,
                event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                actor=StudioActor.SYSTEM, payload_schema_version="studio-runtime-initialized-v1", payload={}, idempotency_key="runtime-ack-2",
            )
        )
        source_message = LearningMessage(session_id=learning_session_id, role="student", content="Studio acknowledgement")
        session.add(source_message)
        session.flush()
        execution = AIExecution(
            task=ModelTask.TUTOR.value, provider="fixture", model="fixture-tutor", latency_ms=1,
            success=True, operation_type="tutor_turn", student_id=student_id,
            learning_session_id=learning_session_id, source_message_id=source_message.id,
        )
        session.add(execution)
        session.flush()
        execution_id, source_message_id = execution.id, source_message.id
        session.commit()

    acknowledge_studio_tutor_observation(
        bind=engine, student_id=student_id, observation_id=selection.context.observation_id,
        ai_execution_id=execution_id, source_message_id=source_message_id,
    )
    acknowledge_studio_tutor_observation(
        bind=engine, student_id=student_id, observation_id=selection.context.observation_id,
        ai_execution_id=execution_id, source_message_id=source_message_id,
    )
    with pytest.raises(ValueError, match="AI execution"):
        acknowledge_studio_tutor_observation(
            bind=engine, student_id=student_id, observation_id=selection.context.observation_id,
            ai_execution_id=None, source_message_id=source_message_id,
        )

    with Session(engine) as session:
        state = StudioStateService(session).runtime_state(runtime_id=runtime_id, student_id=student_id)
        assert state["last_tutor_observation_sequence"] == 1
        assert state["latest_event_sequence"] == 2
    engine.dispose()


def test_context_builder_retains_selected_studio_workspace_context() -> None:
    """Studio selection is additive to the established Tutor context builder."""

    class EmptyRetrieval:
        def retrieve(self, **_: object) -> list[object]:
            return []

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE learning_messages, learning_sessions, students, users CASCADE"))
    with Session(engine) as session:
        user = User(identity_provider="fixture", external_subject=f"context-builder-{uuid4().hex}", role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        workspace = StudioTutorWorkspaceContext(
            runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=0,
            snapshot_sequence=0, current_scene_id=None, current_scene_version=None,
            active_subject_key=None, active_activity_key=None, state_payload={}, unseen_events=(), observation_id=None,
        )

        context = TutorContextBuilder(session, retrieval_service=EmptyRetrieval()).build(  # type: ignore[arg-type]
            learning_session=learning_session,
            question="Can you help me?",
            studio_context=workspace,
        )

    assert context.studio_workspace is workspace
    engine.dispose()


def test_failed_selected_observation_cannot_advance_the_watermark() -> None:
    """Provider/capacity failure leaves the Event range eligible for a later turn."""

    from services.studio.tutor_context import (  # noqa: PLC0415 - RED contract
        acknowledge_studio_tutor_observation,
        mark_studio_tutor_observation_failed,
        select_studio_tutor_context,
    )

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE studio_tutor_observations, studio_events, studio_snapshots, studio_runtimes, learning_sessions, students, users CASCADE"))
    with Session(engine) as session:
        user = User(identity_provider="fixture", external_subject=f"runtime-failure-{uuid4().hex}", role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        StudioStateService(session).append_event(
            AppendStudioEventCommand(runtime_id=runtime.id, student_id=student.id, learning_session_id=learning_session.id,
                event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION, actor=StudioActor.SYSTEM,
                payload_schema_version="studio-runtime-initialized-v1", payload={}, idempotency_key="runtime-failure-1")
        )
        runtime_id, student_id, learning_session_id = runtime.id, student.id, learning_session.id
        session.commit()
    selection = select_studio_tutor_context(bind=engine, student_id=student_id, learning_session_id=learning_session_id)
    assert selection is not None and selection.context.observation_id is not None

    mark_studio_tutor_observation_failed(bind=engine, student_id=student_id, observation_id=selection.context.observation_id, failure_code="PROVIDER_FAILURE")
    with pytest.raises(ValueError, match="selected"):
        acknowledge_studio_tutor_observation(
            bind=engine, student_id=student_id, observation_id=selection.context.observation_id,
            ai_execution_id=uuid4(), source_message_id=uuid4(),
        )
    with Session(engine) as session:
        assert StudioStateService(session).runtime_state(runtime_id=runtime_id, student_id=student_id)["last_tutor_observation_sequence"] == 0
    replacement = select_studio_tutor_context(bind=engine, student_id=student_id, learning_session_id=learning_session_id)
    assert replacement is not None
    assert [event.sequence for event in replacement.context.unseen_events] == [1]
    engine.dispose()


def test_acknowledgement_locks_runtime_then_marks_observation_committed() -> None:
    """The replacement State-service operation atomically commits the exact range."""

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE studio_tutor_observations, studio_events, studio_snapshots, studio_runtimes, learning_sessions, students, users CASCADE"))
    with Session(engine) as session:
        user = User(identity_provider="fixture", external_subject=f"runtime-service-ack-{uuid4().hex}", role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        StudioStateService(session).append_event(
            AppendStudioEventCommand(runtime_id=runtime.id, student_id=student.id, learning_session_id=learning_session.id,
                event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION, actor=StudioActor.SYSTEM,
                payload_schema_version="studio-runtime-initialized-v1", payload={}, idempotency_key="runtime-service-ack-1")
        )
        observation = StudioStateService(session).create_tutor_observation(
            CreateTutorObservationCommand(
                runtime_id=runtime.id, student_id=student.id, from_event_sequence=1, through_event_sequence=1,
            )
        )
        source_message = LearningMessage(session_id=learning_session.id, role="student", content="Studio acknowledgement")
        session.add(source_message)
        session.flush()
        execution = AIExecution(
            task=ModelTask.TUTOR.value, provider="fixture", model="fixture-tutor", latency_ms=1,
            success=True, operation_type="tutor_turn", student_id=student.id,
            learning_session_id=learning_session.id, source_message_id=source_message.id,
        )
        session.add(execution)
        session.flush()
        runtime_id, student_id, observation_id, execution_id, source_message_id = (
            runtime.id, student.id, observation.id, execution.id, source_message.id,
        )
        session.commit()

    with Session(engine) as session:
        service = StudioStateService(session)
        service.advance_tutor_observation_watermark(
            observation_id=observation_id, student_id=student_id,
            ai_execution_id=execution_id, source_message_id=source_message_id,
        )
        session.commit()
    with Session(engine) as session:
        observation = session.get(StudioTutorObservation, observation_id)
        assert observation is not None and observation.status == "COMMITTED" and observation.completed_at is not None
        assert StudioStateService(session).runtime_state(runtime_id=runtime_id, student_id=student_id)["last_tutor_observation_sequence"] == 1
    engine.dispose()


def test_server_owned_history_is_runtime_session_scoped_and_bounded() -> None:
    """Older Studio history is typed, ordered, bounded, and never cross-Student."""

    from services.studio.history import (  # noqa: PLC0415 - RED contract
        MAX_STUDIO_HISTORY_EVENTS,
        STUDIO_HISTORY_POLICY_VERSION,
        StudioHistoryAccessDenied,
        StudioHistoryService,
    )

    assert STUDIO_HISTORY_POLICY_VERSION == "studio-history-v1"
    assert MAX_STUDIO_HISTORY_EVENTS == 100

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE studio_tutor_observations, studio_events, studio_snapshots, studio_runtimes, learning_sessions, students, users CASCADE"))
    with Session(engine) as session:
        user = User(identity_provider="fixture", external_subject=f"runtime-history-{uuid4().hex}", role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning_session = LearningSession(student_id=student.id, subject="MATH")
        session.add(learning_session)
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        for sequence in range(1, MAX_STUDIO_HISTORY_EVENTS + 2):
            StudioStateService(session).append_event(
                AppendStudioEventCommand(runtime_id=runtime.id, student_id=student.id, learning_session_id=learning_session.id,
                    event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION, actor=StudioActor.SYSTEM,
                    payload_schema_version="studio-runtime-initialized-v1", payload={}, idempotency_key=f"runtime-history-{sequence}")
            )
        runtime_id, student_id, learning_session_id = runtime.id, student.id, learning_session.id
        session.commit()

    with Session(engine) as session:
        history = StudioHistoryService(session).events_through(
            student_id=student_id,
            learning_session_id=learning_session_id,
            runtime_id=runtime_id,
            through_sequence=MAX_STUDIO_HISTORY_EVENTS + 1,
            limit=2,
        )
        assert [event.sequence for event in history] == [MAX_STUDIO_HISTORY_EVENTS, MAX_STUDIO_HISTORY_EVENTS + 1]
        maximum_history = StudioHistoryService(session).events_through(
            student_id=student_id,
            learning_session_id=learning_session_id,
            runtime_id=runtime_id,
            through_sequence=MAX_STUDIO_HISTORY_EVENTS + 1,
            limit=MAX_STUDIO_HISTORY_EVENTS,
        )
        assert len(maximum_history) == MAX_STUDIO_HISTORY_EVENTS
        assert [event.sequence for event in maximum_history] == list(range(2, MAX_STUDIO_HISTORY_EVENTS + 2))
        with pytest.raises(StudioHistoryAccessDenied):
            StudioHistoryService(session).events_through(
                student_id=uuid4(), learning_session_id=learning_session_id, runtime_id=runtime_id,
                through_sequence=MAX_STUDIO_HISTORY_EVENTS + 1, limit=2,
            )
        with pytest.raises(ValueError, match="bounded"):
            StudioHistoryService(session).events_through(
                student_id=student_id, learning_session_id=learning_session_id, runtime_id=runtime_id,
                through_sequence=MAX_STUDIO_HISTORY_EVENTS + 1, limit=MAX_STUDIO_HISTORY_EVENTS + 1,
            )
    engine.dispose()


def test_acknowledgement_rejects_a_tutor_execution_from_another_learning_session() -> None:
    """A same-Student Tutor execution is not provenance for a different Studio session."""

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE studio_tutor_observations, studio_events, studio_snapshots, studio_runtimes, ai_executions, learning_sessions, students, users CASCADE"))
    with Session(engine) as session:
        user = User(identity_provider="fixture", external_subject=f"runtime-provenance-{uuid4().hex}", role="STUDENT")
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        runtime_session = LearningSession(student_id=student.id, subject="MATH")
        other_session = LearningSession(student_id=student.id, subject="MATH")
        session.add_all((runtime_session, other_session))
        session.flush()
        runtime = StudioStateService(session).get_or_create_runtime(
            student_id=student.id,
            learning_session_id=runtime_session.id,
        )
        StudioStateService(session).append_event(
            AppendStudioEventCommand(
                runtime_id=runtime.id, student_id=student.id, learning_session_id=runtime_session.id,
                event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                actor=StudioActor.SYSTEM, payload_schema_version="studio-runtime-initialized-v1", payload={},
                idempotency_key="runtime-provenance-1",
            )
        )
        observation = StudioStateService(session).create_tutor_observation(
            CreateTutorObservationCommand(
                runtime_id=runtime.id, student_id=student.id, from_event_sequence=1, through_event_sequence=1,
            )
        )
        source_message = LearningMessage(session_id=runtime_session.id, role="student", content="Studio acknowledgement")
        session.add(source_message)
        session.flush()
        unrelated_execution = AIExecution(
            task=ModelTask.TUTOR.value,
            provider="fixture",
            model="fixture-tutor",
            latency_ms=1,
            success=True,
            operation_type="tutor_turn",
            student_id=student.id,
            learning_session_id=other_session.id,
            source_message_id=source_message.id,
        )
        session.add(unrelated_execution)
        session.flush()
        runtime_id, student_id, observation_id, execution_id, source_message_id = (
            runtime.id,
            student.id,
            observation.id,
            unrelated_execution.id,
            source_message.id,
        )
        session.commit()

    with Session(engine) as session:
        with pytest.raises(ValueError, match="AI execution"):
            StudioStateService(session).advance_tutor_observation_watermark(
                observation_id=observation_id,
                student_id=student_id,
                ai_execution_id=execution_id,
                source_message_id=source_message_id,
            )
        session.expire_all()
        observation = session.get(StudioTutorObservation, observation_id)
        runtime = session.get(StudioRuntime, runtime_id)
        assert observation is not None and observation.status == "SELECTED"
        assert observation.ai_execution_id is None
        assert runtime is not None and runtime.last_tutor_observation_sequence == 0
    engine.dispose()


@pytest.mark.parametrize(
    ("case", "task", "success", "session_relation", "student_relation"),
    (
        ("wrong-task", ModelTask.EMBEDDING.value, True, "exact", "exact"),
        ("failed-tutor", ModelTask.TUTOR.value, False, "exact", "exact"),
        ("null-session", ModelTask.TUTOR.value, True, "null", "exact"),
        ("different-student", ModelTask.TUTOR.value, True, "other", "other"),
    ),
)
def test_acknowledgement_rejects_each_non_provenance_execution(
    case: str,
    task: str,
    success: bool,
    session_relation: str,
    student_relation: str,
) -> None:
    """Only the successful Tutor execution for this exact runtime may acknowledge it."""

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE studio_tutor_observations, studio_events, studio_snapshots, studio_runtimes, ai_executions, learning_sessions, students, users CASCADE"))
    with Session(engine) as session:
        student, learning_session, runtime, observation, source_message = _selected_observation_fixture(session, case)
        execution_student = student
        execution_session = learning_session
        if student_relation == "other":
            other_user = User(identity_provider="fixture", external_subject=f"runtime-provenance-other-{case}-{uuid4().hex}", role="STUDENT")
            session.add(other_user)
            session.flush()
            execution_student = Student(user_id=other_user.id)
            session.add(execution_student)
            session.flush()
            execution_session = LearningSession(student_id=execution_student.id, subject="MATH")
            session.add(execution_session)
            session.flush()
        elif session_relation == "null":
            execution_session = None
        execution = AIExecution(
            task=task,
            provider="fixture",
            model="fixture-model",
            latency_ms=1,
            success=success,
            operation_type="fixture",
            student_id=execution_student.id,
            learning_session_id=None if execution_session is None else execution_session.id,
            source_message_id=source_message.id,
        )
        session.add(execution)
        session.flush()
        runtime_id, student_id, observation_id, execution_id, source_message_id = (
            runtime.id, student.id, observation.id, execution.id, source_message.id,
        )
        session.commit()

    with Session(engine) as session:
        with pytest.raises(ValueError, match="AI execution"):
            StudioStateService(session).advance_tutor_observation_watermark(
                observation_id=observation_id,
                student_id=student_id,
                ai_execution_id=execution_id,
                source_message_id=source_message_id,
            )
        _assert_acknowledgement_unchanged(session, observation_id=observation_id, runtime_id=runtime_id)
    engine.dispose()


def test_acknowledgement_rejects_nonexistent_execution_without_mutation() -> None:
    """A missing execution cannot become a provenance link or consume Events."""

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE studio_tutor_observations, studio_events, studio_snapshots, studio_runtimes, ai_executions, learning_sessions, students, users CASCADE"))
    with Session(engine) as session:
        student, _learning_session, runtime, observation, source_message = _selected_observation_fixture(session, "missing")
        runtime_id, student_id, observation_id, source_message_id = (
            runtime.id, student.id, observation.id, source_message.id,
        )
        session.commit()

    with Session(engine) as session:
        with pytest.raises(ValueError, match="AI execution"):
            StudioStateService(session).advance_tutor_observation_watermark(
                observation_id=observation_id,
                student_id=student_id,
                ai_execution_id=uuid4(),
                source_message_id=source_message_id,
            )
        _assert_acknowledgement_unchanged(session, observation_id=observation_id, runtime_id=runtime_id)
    engine.dispose()


def test_acknowledgement_rejects_null_execution_without_mutation() -> None:
    """A selected range cannot be consumed without the primary Tutor execution."""

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE studio_tutor_observations, studio_events, studio_snapshots, studio_runtimes, ai_executions, learning_sessions, students, users CASCADE"))
    with Session(engine) as session:
        student, _learning_session, runtime, observation, _source_message = _selected_observation_fixture(session, "null-execution")
        runtime_id, student_id, observation_id = runtime.id, student.id, observation.id
        session.commit()

    with Session(engine) as session:
        with pytest.raises(ValueError, match="AI execution"):
            StudioStateService(session).advance_tutor_observation_watermark(
                observation_id=observation_id,
                student_id=student_id,
                ai_execution_id=None,
                source_message_id=uuid4(),
            )
        session.expire_all()
        observation = session.get(StudioTutorObservation, observation_id)
        runtime = session.get(StudioRuntime, runtime_id)
        assert observation is not None and observation.status == "SELECTED"
        assert observation.ai_execution_id is None
        assert observation.completed_at is None
        assert runtime is not None and runtime.last_tutor_observation_sequence == 0
    engine.dispose()


def test_acknowledgement_rejects_a_successful_tutor_execution_from_another_student_turn() -> None:
    """An earlier successful Tutor turn cannot consume a newer Studio selection."""

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE studio_tutor_observations, studio_events, studio_snapshots, studio_runtimes, ai_executions, learning_messages, learning_sessions, students, users CASCADE"))
    with Session(engine) as session:
        student, learning_session, runtime, observation, _source_message = _selected_observation_fixture(session, "wrong-source")
        earlier_student_message = LearningMessage(session_id=learning_session.id, role="student", content="Earlier turn")
        current_student_message = LearningMessage(session_id=learning_session.id, role="student", content="Current turn")
        session.add_all((earlier_student_message, current_student_message))
        session.flush()
        execution = AIExecution(
            task=ModelTask.TUTOR.value,
            provider="fixture",
            model="fixture-tutor",
            latency_ms=1,
            success=True,
            operation_type="tutor_turn",
            student_id=student.id,
            learning_session_id=learning_session.id,
            source_message_id=earlier_student_message.id,
        )
        session.add(execution)
        session.flush()
        runtime_id, student_id, observation_id, execution_id, current_message_id = (
            runtime.id,
            student.id,
            observation.id,
            execution.id,
            current_student_message.id,
        )
        session.commit()

    with Session(engine) as session:
        with pytest.raises(ValueError, match="AI execution"):
            StudioStateService(session).advance_tutor_observation_watermark(
                observation_id=observation_id,
                student_id=student_id,
                ai_execution_id=execution_id,
                source_message_id=current_message_id,
            )
        _assert_acknowledgement_unchanged(session, observation_id=observation_id, runtime_id=runtime_id)
    engine.dispose()


def test_acknowledgement_links_the_exact_successful_tutor_execution() -> None:
    """The normal provenance predicate attaches the one eligible Tutor execution."""

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE studio_tutor_observations, studio_events, studio_snapshots, studio_runtimes, ai_executions, learning_sessions, students, users CASCADE"))
    with Session(engine) as session:
        student, learning_session, runtime, observation, source_message = _selected_observation_fixture(session, "success")
        execution = AIExecution(
            task=ModelTask.TUTOR.value,
            provider="fixture",
            model="fixture-tutor",
            latency_ms=1,
            success=True,
            operation_type="tutor_turn",
            student_id=student.id,
            learning_session_id=learning_session.id,
            source_message_id=source_message.id,
        )
        session.add(execution)
        session.flush()
        runtime_id, student_id, observation_id, execution_id, source_message_id = (
            runtime.id, student.id, observation.id, execution.id, source_message.id,
        )
        session.commit()

    with Session(engine) as session:
        committed = StudioStateService(session).advance_tutor_observation_watermark(
            observation_id=observation_id,
            student_id=student_id,
            ai_execution_id=execution_id,
            source_message_id=source_message_id,
        )
        session.commit()
        assert committed.status == "COMMITTED"
        assert committed.ai_execution_id == execution_id
    with Session(engine) as session:
        runtime = session.get(StudioRuntime, runtime_id)
        assert runtime is not None and runtime.last_tutor_observation_sequence == 1
    engine.dispose()


def _selected_observation_fixture(session: Session, suffix: str):
    user = User(identity_provider="fixture", external_subject=f"runtime-provenance-{suffix}-{uuid4().hex}", role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id)
    session.add(student)
    session.flush()
    learning_session = LearningSession(student_id=student.id, subject="MATH")
    session.add(learning_session)
    session.flush()
    runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
    StudioStateService(session).append_event(
        AppendStudioEventCommand(
            runtime_id=runtime.id, student_id=student.id, learning_session_id=learning_session.id,
            event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION,
            actor=StudioActor.SYSTEM, payload_schema_version="studio-runtime-initialized-v1", payload={},
            idempotency_key=f"runtime-provenance-{suffix}",
        )
    )
    observation = StudioStateService(session).create_tutor_observation(
        CreateTutorObservationCommand(runtime_id=runtime.id, student_id=student.id, from_event_sequence=1, through_event_sequence=1)
    )
    source_message = LearningMessage(session_id=learning_session.id, role="student", content="Studio acknowledgement")
    session.add(source_message)
    session.flush()
    return student, learning_session, runtime, observation, source_message


def _assert_acknowledgement_unchanged(session: Session, *, observation_id, runtime_id) -> None:
    session.expire_all()
    observation = session.get(StudioTutorObservation, observation_id)
    runtime = session.get(StudioRuntime, runtime_id)
    assert observation is not None and observation.status == "SELECTED"
    assert observation.ai_execution_id is None
    assert runtime is not None and runtime.last_tutor_observation_sequence == 0
