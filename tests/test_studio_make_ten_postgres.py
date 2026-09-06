"""Production Make-Ten activity contracts, state, protocol, and Tutor-continuation tests."""

from __future__ import annotations

import os
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.auth import AuthenticatedPrincipal, UserRole
from services.platform.auth.clerk import get_current_principal
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import LearningMessage, LearningSegment, LearningSession, StudioEvent, StudioRuntime, StudioScene, StudioStudentInteraction, Student, User
from services.platform.db.session import get_session
from services.platform.safety import SafetyPolicyService
from services.retrieval.service import RetrievalService
from services.studio.contracts import AppendStudioEventCommand, CreateSceneCommand, StudioActor
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.router import WorkspaceAuthorityContext, WorkspaceDecisionStatus, WorkspaceExecutionMode, route_workspace_intent
from services.studio.service import InvalidStudioLineage, StaleSceneVersion, StudioStateError, StudioStateService
from services.studio.subjects import PRODUCTION_CURRENT_PROFILE_VERSIONS, production_subject_registry
from services.studio.workspace_intent import WorkspaceIntent
from services.tutor.context import TutorContextBuilder
from services.tutor.runtime import TutorRuntime


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Make-Ten activity contracts",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE studio_canvas_specialist_runs, studio_tutor_observations, "
                "studio_student_interactions, studio_events, studio_snapshots, studio_scenes, "
                "studio_runtimes, learning_messages, learning_segments, learning_sessions, students, users CASCADE"
            )
        )
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _student(session: Session, subject: str) -> Student:
    user = User(identity_provider="clerk", external_subject=subject, email=f"{subject}@example.test", role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name=subject)
    session.add(student)
    session.flush()
    return student


def _learning_session(session: Session, student: Student) -> LearningSession:
    learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
    session.add(learning_session)
    session.flush()
    return learning_session


def _intent() -> WorkspaceIntent:
    return WorkspaceIntent.model_validate(
        {
            "version": "workspace-intent-v1",
            "action": "OPEN_ACTIVITY",
            "subject_key": "MATH",
            "concept_keys": ["make-ten"],
            "learning_goal": "Make a full ten and see what remains.",
            "activity_hint": "ten_frame_group_transfer",
            "representation_need": "INTERACTIVE",
            "expected_student_response_mode": "WORKSPACE",
            "presentation_sequence": "PARALLEL",
            "source_references": [],
            "safe_text_fallback": "Let's make a full ten together.",
        }
    )


def _make_ten_scene_command(
    student: Student,
    learning_session: LearningSession,
    *,
    source_segment_id: UUID | None = None,
    source_message_id: UUID | None = None,
) -> CreateSceneCommand:
    from services.studio.subjects.math_make_ten import (  # noqa: PLC0415 - RED contract
        ACTIVITY_KEY,
        ACTIVITY_VERSION,
        ACCESSIBILITY_PAYLOAD,
        MATH_PROFILE_VERSION,
        RENDERER_KEY,
        RENDERER_VERSION,
        SCENE_PAYLOAD_SCHEMA_VERSION,
        make_ten_scene_seed,
    )

    return CreateSceneCommand(
        student_id=student.id,
        learning_session_id=learning_session.id,
        subject_key="MATH",
        subject_profile_version=MATH_PROFILE_VERSION,
        concept_keys=("make-ten",),
        activity_key=ACTIVITY_KEY,
        artifact_type="interactive-activity",
        renderer_key=RENDERER_KEY,
        renderer_version=RENDERER_VERSION,
        activity_contract_version=ACTIVITY_VERSION,
        payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
        seed_payload=make_ten_scene_seed(),
        accessibility_payload=ACCESSIBILITY_PAYLOAD,
        locale="en",
        direction="auto",
        source_segment_id=source_segment_id,
        source_message_id=source_message_id,
    )


def _make_ten_workspace_audit() -> dict[str, object]:
    decision = route_workspace_intent(
        _intent(),
        WorkspaceAuthorityContext(
            registry=production_subject_registry(),
            current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS,
        ),
    )
    return {
        "intent_status": "VALID",
        "intent": _intent().model_dump(mode="json"),
        "decision": decision.as_audit_payload(),
    }


def _tutor_source(session: Session, learning_session: LearningSession) -> tuple[LearningSegment, LearningMessage]:
    segment = LearningSegment(session_id=learning_session.id, sequence=1)
    session.add(segment)
    session.flush()
    message = LearningMessage(
        session_id=learning_session.id,
        segment_id=segment.id,
        role="tutor",
        content="Let us make a full ten.",
    )
    session.add(message)
    session.flush()
    return segment, message


def _unrelated_accepted_scene(
    *,
    runtime_id: UUID,
    student: Student,
    learning_session: LearningSession,
    source_segment_id: UUID,
    source_message_id: UUID,
) -> StudioScene:
    """Fixture-only legacy Scene: valid DB lineage but never a registered Make-Ten contract."""

    return StudioScene(
        studio_runtime_id=runtime_id,
        student_id=student.id,
        learning_session_id=learning_session.id,
        source_segment_id=source_segment_id,
        source_message_id=source_message_id,
        subject_key="SCIENCE",
        subject_profile_version="subject-profile-v1",
        concept_keys=["unrelated"],
        activity_key="unrelated-accepted-scene",
        artifact_type="interactive-activity",
        renderer_key="unrelated-renderer",
        renderer_version="unrelated-renderer-v1",
        activity_contract_version="unrelated-activity-v1",
        payload_schema_version="unrelated-scene-v1",
        seed_payload={},
        accessibility_payload={},
        locale="en",
        direction="auto",
    )


def _activate(service: StudioStateService, *, runtime_id: UUID, student: Student, learning_session: LearningSession, scene: StudioScene) -> None:
    service.append_event(
        AppendStudioEventCommand(
            runtime_id=runtime_id,
            student_id=student.id,
            learning_session_id=learning_session.id,
            event_kind="studio.scene.activated",
            event_schema_version=CORE_EVENT_SCHEMA_VERSION,
            actor=StudioActor.SYSTEM,
            payload_schema_version="studio-scene-activated-v1",
            payload={},
            scene_id=scene.id,
            base_scene_version=scene.scene_version,
            idempotency_key=f"activate:{scene.id}",
        )
    )


def _transfer_command(
    *,
    runtime_id: UUID,
    student: Student,
    learning_session: LearningSession,
    scene: StudioScene,
    item_id: str,
    from_group_id: str = "ones-group",
    to_group_id: str = "ten-frame",
    idempotency_key: str = "make-ten-transfer-1",
    base_scene_version: int | None = None,
) -> AppendStudioEventCommand:
    from services.studio.subjects.math_make_ten import TRANSFER_ITEM_ACTION_KEY, TRANSFER_PAYLOAD_SCHEMA_VERSION  # noqa: PLC0415 - RED contract

    return AppendStudioEventCommand(
        runtime_id=runtime_id,
        student_id=student.id,
        learning_session_id=learning_session.id,
        event_kind=None,
        event_schema_version=None,
        actor=StudioActor.STUDENT,
        action_key=TRANSFER_ITEM_ACTION_KEY,
        payload_schema_version=TRANSFER_PAYLOAD_SCHEMA_VERSION,
        payload={"item_id": item_id, "from_group_id": from_group_id, "to_group_id": to_group_id},
        scene_id=scene.id,
        base_scene_version=scene.scene_version if base_scene_version is None else base_scene_version,
        idempotency_key=idempotency_key,
    )


def _submit_command(
    *,
    runtime_id: UUID,
    student: Student,
    learning_session: LearningSession,
    scene: StudioScene,
    ten_frame_item_ids: list[str],
    ones_group_item_ids: list[str],
    idempotency_key: str,
) -> AppendStudioEventCommand:
    from services.studio.subjects.math_make_ten import SUBMIT_CONFIGURATION_ACTION_KEY, SUBMIT_PAYLOAD_SCHEMA_VERSION  # noqa: PLC0415 - RED contract

    return AppendStudioEventCommand(
        runtime_id=runtime_id,
        student_id=student.id,
        learning_session_id=learning_session.id,
        event_kind=None,
        event_schema_version=None,
        actor=StudioActor.STUDENT,
        action_key=SUBMIT_CONFIGURATION_ACTION_KEY,
        payload_schema_version=SUBMIT_PAYLOAD_SCHEMA_VERSION,
        payload={"ten_frame_item_ids": ten_frame_item_ids, "ones_group_item_ids": ones_group_item_ids},
        scene_id=scene.id,
        base_scene_version=scene.scene_version,
        idempotency_key=idempotency_key,
    )


def test_make_ten_transfer_commits_the_same_scene_and_snapshot_version(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """An accepted transfer must not make the strict Snapshot projection unreadable."""
    from services.studio.subjects.math_make_ten import make_ten_scene_seed

    with postgres_session_factory.begin() as session:
        student = _student(session, "make-ten-version-invariant")
        learning_session = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        scene = service.accept_scene(_make_ten_scene_command(student, learning_session))
        _activate(service, runtime_id=runtime.id, student=student, learning_session=learning_session, scene=scene)
        before = service.runtime_state(runtime_id=runtime.id, student_id=student.id)["snapshot"]
        assert scene.scene_version == before["current_scene_version"] == 2
        result = service.append_event(_transfer_command(
            runtime_id=runtime.id,
            student=student,
            learning_session=learning_session,
            scene=scene,
            item_id=make_ten_scene_seed()["groups"]["ones-group"]["item_ids"][0],
        ))
        student_id, runtime_id, scene_id, event_id = student.id, runtime.id, scene.id, result.event.id

    with postgres_session_factory() as session:
        scene = session.get(StudioScene, scene_id)
        event = session.get(StudioEvent, event_id)
        snapshot = StudioStateService(session).runtime_state(runtime_id=runtime_id, student_id=student_id)["snapshot"]
        assert event.resulting_scene_version == scene.scene_version == 3
        assert snapshot["current_scene_version"] == 3

    from services.studio.feed import StudioEventFeed

    sequence, events, frame = StudioEventFeed(session_factory=postgres_session_factory)._snapshot_and_events(
        student_id=student_id, runtime_id=runtime_id, after_sequence=2,
    )
    assert sequence == 3
    assert len(events) == 1
    assert frame["current_scene_version"] == frame["active_scene_contract"]["scene_version"] == 3
    client = _client(postgres_session_factory, subject="make-ten-version-invariant")
    try:
        response = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot")
        assert response.status_code == 200
        assert response.json()["current_scene_version"] == response.json()["active_scene_contract"]["scene_version"] == 3
    finally:
        _clear_overrides()


@pytest.mark.parametrize("mutation", ["transfer", "activation", "replacement"])
def test_feed_materializes_one_owned_window_before_expiring_commit(
    postgres_session_factory: sessionmaker[Session], mutation: str,
) -> None:
    """Post-commit ORM refresh must not mix a later writer with the captured window."""
    import json
    from concurrent.futures import ThreadPoolExecutor
    from copy import deepcopy
    from threading import Event

    import psycopg
    from sqlalchemy import event as sqlalchemy_event

    from services.platform.db.models import StudioSnapshot
    from services.studio.feed import StudioEventFeed, format_sse_frame
    from services.studio.subjects import process_sequence as science
    from services.studio.subjects.math_make_ten import make_ten_scene_seed

    engine = postgres_session_factory.kw["bind"]
    # Unlike the surrounding legacy fixture factory, every Session in this
    # regression retains production's default expire_on_commit=True.
    with Session(engine) as session:
        student = _student(session, f"feed-window-{mutation}")
        learning_session = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        service.append_event(AppendStudioEventCommand(
            runtime_id=runtime.id, student_id=student.id, learning_session_id=learning_session.id,
            event_kind="studio.runtime.initialized", event_schema_version=CORE_EVENT_SCHEMA_VERSION,
            actor=StudioActor.SYSTEM, payload_schema_version="studio-runtime-initialized-v1",
            payload={}, idempotency_key="offset-runtime-counter",
        ))
        scene = service.accept_scene(_make_ten_scene_command(student, learning_session))
        if mutation != "activation":
            _activate(service, runtime_id=runtime.id, student=student, learning_session=learning_session, scene=scene)
        student_id, session_id, runtime_id, scene_id = student.id, learning_session.id, runtime.id, scene.id
        session.commit()

    reader_committed, writer_done = Event(), Event()
    post_commit_sql: list[str] = []
    payload_references: list[dict] = []
    captured_objects: list[object] = []
    old_version, watermark = (1, 2) if mutation == "activation" else (2, 3)
    assert old_version != watermark  # Runtime sequence is not a Scene version.

    class BarrierSession(Session):
        def commit(self) -> None:
            assert self.expire_on_commit is True
            for obj in captured_objects:
                for key in ("seed_payload", "state_payload", "payload"):
                    value = obj.__dict__.get(key)
                    if isinstance(value, dict):
                        payload_references.append(value)
            super().commit()
            reader_committed.set()
            assert writer_done.wait(10), "Writer did not finish the synchronized commit"

    # Hold distinct physical PostgreSQL connections throughout the race.
    with engine.connect() as reader_connection, engine.connect() as writer_connection:
        assert reader_connection.execute(text("select pg_backend_pid()")).scalar_one() != writer_connection.execute(text("select pg_backend_pid()")).scalar_one()
        reader_connection.rollback()
        writer_connection.rollback()
        reader = BarrierSession(reader_connection)
        sqlalchemy_event.listen(reader, "loaded_as_persistent", lambda _session, obj: captured_objects.append(obj))

        def observe_sql(_connection, _cursor, statement, _parameters, _context, _many):
            if reader_committed.is_set():
                post_commit_sql.append(statement)

        sqlalchemy_event.listen(reader_connection, "before_cursor_execute", observe_sql)

        def write_later_window():
            try:
                assert reader_committed.wait(10), "Reader did not capture and commit its window"
                with Session(writer_connection) as session:
                    service = StudioStateService(session)
                    student = session.get(Student, student_id)
                    learning_session = session.get(LearningSession, session_id)
                    scene = session.get(StudioScene, scene_id)
                    if mutation == "transfer":
                        service.append_event(_transfer_command(
                            runtime_id=runtime_id, student=student, learning_session=learning_session,
                            scene=scene, item_id=make_ten_scene_seed()["groups"]["ones-group"]["item_ids"][0],
                        ))
                    elif mutation == "activation":
                        _activate(service, runtime_id=runtime_id, student=student, learning_session=learning_session, scene=scene)
                    else:
                        service.append_event(AppendStudioEventCommand(
                            runtime_id=runtime_id, student_id=student_id, learning_session_id=session_id,
                            event_kind="studio.scene.status_changed", event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                            actor=StudioActor.SYSTEM, payload_schema_version="studio-scene-status-v1",
                            payload={"status": "SUPERSEDED"}, scene_id=scene.id,
                            base_scene_version=scene.scene_version, idempotency_key="replace-old-scene",
                        ))
                        scene = service.accept_scene(CreateSceneCommand(
                            student_id=student_id, learning_session_id=session_id,
                            subject_key="SCIENCE", subject_profile_version=science.SCIENCE_PROFILE_VERSION,
                            concept_keys=("filtration-sequence",), activity_key=science.ACTIVITY_KEY,
                            artifact_type="interactive-activity", renderer_key=science.RENDERER_KEY,
                            renderer_version=science.RENDERER_VERSION, activity_contract_version=science.ACTIVITY_VERSION,
                            payload_schema_version=science.SCENE_PAYLOAD_SCHEMA_VERSION,
                            seed_payload=science.process_sequence_scene_seed(), accessibility_payload=science.ACCESSIBILITY_PAYLOAD,
                            locale="ar", direction="rtl",
                        ))
                        _activate(service, runtime_id=runtime_id, student=student, learning_session=learning_session, scene=scene)
                    snapshot = session.scalar(select(StudioSnapshot).where(StudioSnapshot.studio_runtime_id == runtime_id))
                    assert snapshot.current_scene_version == scene.scene_version
                    assert snapshot.latest_event_sequence > watermark
                    new_identity = (str(scene.id), scene.scene_version, snapshot.latest_event_sequence)
                    session.commit()
                    return new_identity
            finally:
                writer_done.set()

        with ThreadPoolExecutor(max_workers=1) as executor:
            writer = executor.submit(write_later_window)
            result = StudioEventFeed(session_factory=lambda: reader)._snapshot_and_events(
                student_id=student_id, runtime_id=runtime_id, after_sequence=0,
            )
            new_scene_id, new_version, new_watermark = writer.result(timeout=10)
        latest, frames, frame = result
        assert latest == frame["latest_event_sequence"] == watermark
        assert frame["current_scene_id"] == str(scene_id)
        assert frame["current_scene_version"] == old_version
        assert [event["sequence"] for event in frames] == list(range(1, watermark + 1))
        if mutation == "activation":
            assert frame["active_scene_contract"] is frame["active_scene_seed"] is None
        else:
            assert frame["active_scene_contract"]["scene_id"] == str(scene_id)
            assert frame["active_scene_contract"]["scene_version"] == 2
            assert frame["active_scene_seed"] == make_ten_scene_seed()
        assert post_commit_sql == [], "Serialization reopened a read after commit"
        assert not reader.in_transaction()
        # Mutating retained ORM JSON containers must not change returned owned
        # data, including nested Snapshot, Scene seed, and event payloads.
        frozen = deepcopy(result)
        def mutate_nested(value):
            if isinstance(value, dict):
                for child in value.values():
                    mutate_nested(child)
            elif isinstance(value, list):
                value.append("test-only-detached-mutation")
        for payload in payload_references:
            mutate_nested(payload)
        assert result == frozen
        encoded = format_sse_frame(frame)
        assert json.loads(encoded.split("data: ", 1)[1]) == frame
        assert post_commit_sql == []

    # A later explicit window catches every committed event exactly once by
    # cursor; it does not apply a semantic action a second time.
    feed = StudioEventFeed(session_factory=lambda: Session(engine))
    newest, catchup, snapshot = feed._snapshot_and_events(student_id=student_id, runtime_id=runtime_id, after_sequence=watermark)
    assert newest == snapshot["latest_event_sequence"] == new_watermark
    assert [event["sequence"] for event in catchup] == list(range(watermark + 1, newest + 1))
    assert snapshot["current_scene_id"] == snapshot["active_scene_contract"]["scene_id"] == new_scene_id
    assert snapshot["current_scene_version"] == snapshot["active_scene_contract"]["scene_version"] == new_version
    if mutation == "transfer":
        assert new_version == 3 and newest == 4
    if mutation == "replacement":
        assert new_scene_id != str(scene_id)
        assert snapshot["active_scene_contract"]["subject_key"] == "SCIENCE"
        assert snapshot["active_scene_seed"] == science.process_sequence_scene_seed()
    again = feed._snapshot_and_events(student_id=student_id, runtime_id=runtime_id, after_sequence=newest)
    assert again == (newest, [], snapshot)

    # Exercise the actual stream formatter/cursor with a real LISTEN connection.
    listener_url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    feed = StudioEventFeed(session_factory=lambda: Session(engine), listener_factory=lambda: psycopg.connect(listener_url, autocommit=True))
    stream = feed.stream(student_id=student_id, runtime_id=runtime_id, after_sequence=watermark)
    try:
        for expected in catchup:
            assert next(stream) == format_sse_frame(expected, event_id=expected["sequence"])
        assert next(stream) == format_sse_frame(snapshot)
    finally:
        stream.close()


def test_make_ten_is_the_current_exact_math_capability_without_rewriting_math_v1() -> None:
    from services.studio.subjects.math_make_ten import (  # noqa: PLC0415 - RED contract
        ACTIVITY_KEY,
        ACTIVITY_VERSION,
        MATH_PROFILE_VERSION,
        RENDERER_KEY,
        RENDERER_VERSION,
        SUBMIT_CONFIGURATION_ACTION_KEY,
        TRANSFER_ITEM_ACTION_KEY,
    )

    registry = production_subject_registry()
    assert PRODUCTION_CURRENT_PROFILE_VERSIONS["MATH"] == MATH_PROFILE_VERSION
    assert registry.activities_for_profile("MATH", "subject-profile-v1") == ()
    activity = registry.resolve_activity("MATH", MATH_PROFILE_VERSION, ACTIVITY_KEY, ACTIVITY_VERSION)
    renderer = registry.resolve_renderer("MATH", MATH_PROFILE_VERSION, RENDERER_KEY, RENDERER_VERSION)
    assert {action.action_key for action in activity.actions} == {TRANSFER_ITEM_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY}
    assert renderer.interactive is True
    decision = route_workspace_intent(
        _intent(),
        WorkspaceAuthorityContext(registry=registry, current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS),
    )
    assert decision.status is WorkspaceDecisionStatus.ROUTED
    assert decision.mode is WorkspaceExecutionMode.KNOWN_INTERACTIVE
    assert decision.selected_activity_key == ACTIVITY_KEY
    assert decision.selected_activity_version == ACTIVITY_VERSION
    unhinted = route_workspace_intent(
        WorkspaceIntent.model_validate({**_intent().model_dump(mode="json"), "activity_hint": None}),
        WorkspaceAuthorityContext(registry=registry, current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS),
    )
    assert unhinted.status is WorkspaceDecisionStatus.FALLBACK


def test_make_ten_transfer_and_submit_are_durable_rebuildable_and_truthful(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    from services.studio.subjects.math_make_ten import make_ten_scene_seed  # noqa: PLC0415 - RED contract

    with postgres_session_factory.begin() as session:
        student = _student(session, "make-ten-state")
        learning_session = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        scene = service.accept_scene(_make_ten_scene_command(student, learning_session))
        _activate(service, runtime_id=runtime.id, student=student, learning_session=learning_session, scene=scene)
        source_item = make_ten_scene_seed()["groups"]["ones-group"]["item_ids"][0]
        transfer_command = _transfer_command(
            runtime_id=runtime.id,
            student=student,
            learning_session=learning_session,
            scene=scene,
            item_id=source_item,
        )
        transfer = service.append_event(transfer_command)
        assert transfer.interaction is None
        assert transfer.event.payload == {
            "action": {"item_id": source_item, "from_group_id": "ones-group", "to_group_id": "ten-frame"}
        }
        projection = service.runtime_state(runtime_id=runtime.id, student_id=student.id)["snapshot"]
        activity_state = projection["state_payload"]["ten_frame_group_transfer"]
        assert len(activity_state["groups"]["ten-frame"]["item_ids"]) == 10
        assert len(activity_state["groups"]["ones-group"]["item_ids"]) == 5
        assert sorted(
            activity_state["groups"]["ten-frame"]["item_ids"] + activity_state["groups"]["ones-group"]["item_ids"]
        ) == sorted(item["id"] for item in make_ten_scene_seed()["items"])
        assert service.rebuild_snapshot(runtime_id=runtime.id, student_id=student.id) == projection

        replay = service.append_event(transfer_command)
        assert replay.replayed is True
        assert replay.event.id == transfer.event.id
        assert scene.scene_version == 3
        assert service.runtime_state(runtime_id=runtime.id, student_id=student.id)["snapshot"]["current_scene_version"] == 3

        before_invalid = service.runtime_state(runtime_id=runtime.id, student_id=student.id)
        with pytest.raises(StudioStateError, match="Payload|Item"):
            service.append_event(
                _transfer_command(
                    runtime_id=runtime.id,
                    student=student,
                    learning_session=learning_session,
                    scene=scene,
                    item_id="unknown-item",
                    idempotency_key="make-ten-invalid-item",
                )
            )
        assert service.runtime_state(runtime_id=runtime.id, student_id=student.id) == before_invalid

        with pytest.raises(StaleSceneVersion):
            service.append_event(
                _transfer_command(
                    runtime_id=runtime.id,
                    student=student,
                    learning_session=learning_session,
                    scene=scene,
                    item_id=source_item,
                    idempotency_key="make-ten-stale",
                    base_scene_version=scene.scene_version - 1,
                )
            )

        actual_ten = list(activity_state["groups"]["ten-frame"]["item_ids"])
        actual_ones = list(activity_state["groups"]["ones-group"]["item_ids"])
        mismatched = service.append_event(
            _submit_command(
                runtime_id=runtime.id,
                student=student,
                learning_session=learning_session,
                scene=scene,
                ten_frame_item_ids=actual_ten[:-1],
                ones_group_item_ids=actual_ones + [actual_ten[-1]],
                idempotency_key="make-ten-submit-mismatch",
            )
        )
        assert mismatched.interaction is not None
        assert mismatched.event.payload["validation"] == {
            "status": "INVALID",
            "feedback_code": "SUBMITTED_CONFIGURATION_DOES_NOT_MATCH_STATE",
            "next_action_keys": ["TRANSFER_ITEM", "SUBMIT_CONFIGURATION"],
        }
        correct = service.append_event(
            _submit_command(
                runtime_id=runtime.id,
                student=student,
                learning_session=learning_session,
                scene=scene,
                ten_frame_item_ids=actual_ten,
                ones_group_item_ids=actual_ones,
                idempotency_key="make-ten-submit-complete",
            )
        )
        assert correct.interaction is not None
        assert correct.event.resulting_scene_version == scene.scene_version == 5
        assert service.runtime_state(runtime_id=runtime.id, student_id=student.id)["snapshot"]["current_scene_version"] == 5
        assert correct.event.payload["validation"] == {
            "status": "VALID",
            "feedback_code": "MAKE_TEN_COMPLETE",
            "next_action_keys": [],
        }
        assert service.rebuild_snapshot(runtime_id=runtime.id, student_id=student.id) == service.runtime_state(
            runtime_id=runtime.id, student_id=student.id
        )["snapshot"]

        other = _student(session, "make-ten-other")
        with pytest.raises(InvalidStudioLineage):
            service.append_event(
                _submit_command(
                    runtime_id=runtime.id,
                    student=other,
                    learning_session=learning_session,
                    scene=scene,
                    ten_frame_item_ids=actual_ten,
                    ones_group_item_ids=actual_ones,
                    idempotency_key="make-ten-other-student",
                )
            )


def _client(factory: sessionmaker[Session], *, subject: str) -> TestClient:
    from apps.api.main import app

    def database_session():
        with factory.begin() as session:
            yield session

    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject=subject, role=UserRole.STUDENT, email=f"{subject}@example.test"
    )
    return TestClient(app)


def _clear_overrides() -> None:
    from apps.api.main import app

    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_principal, None)


def test_make_ten_submission_continues_with_original_truth_after_later_record_only_transfer(
    postgres_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.api.routes import student as student_routes
    from services.platform.db.models import ModelTask
    from services.studio.subjects.math_make_ten import (  # noqa: PLC0415 - RED contract
        SUBMIT_CONFIGURATION_ACTION_KEY,
        TRANSFER_ITEM_ACTION_KEY,
        make_ten_scene_seed,
    )

    class Provider:
        calls = 0

        def stream(self, route: ModelRoute, payload: dict[str, object]):
            del route
            self.calls += 1
            source_event = payload["studio_interaction_context"]["source"]["event"]
            live_subject = payload["studio_interaction_context"]["source"]["live_subject"]
            source_groups = source_event["action_payload"]
            source_validation = source_event["validation"]
            current_groups = payload["studio_interaction_context"]["workspace"]["state"]["ten_frame_group_transfer"]["groups"]
            selected_groups = payload["studio_workspace_context"]["snapshot"]["state"]["ten_frame_group_transfer"]["groups"]
            assert len(source_groups["ten_frame_item_ids"]) == 10
            assert len(source_groups["ones_group_item_ids"]) == 5
            assert live_subject["broad_subject"] == "MATH"
            assert live_subject["origin"] == "CANVAS_SCENE"
            assert live_subject["source_scene_id"] == source_event["scene_id"]
            assert source_validation == {
                "status": "VALID",
                "feedback_code": "MAKE_TEN_COMPLETE",
                "next_action_keys": [],
            }
            assert len(current_groups["ten-frame"]["item_ids"]) == 9
            assert len(current_groups["ones-group"]["item_ids"]) == 6
            assert current_groups == selected_groups
            yield StreamDelta("You made a full ten.")
            yield StreamComplete(ModelResult(output={"text": "You made a full ten.", "workspace_intent": None}))

    with postgres_session_factory.begin() as session:
        student = _student(session, "make-ten-api")
        learning_session = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        scene = service.accept_scene(_make_ten_scene_command(student, learning_session))
        _activate(service, runtime_id=runtime.id, student=student, learning_session=learning_session, scene=scene)
        runtime_id, scene_id, scene_version = runtime.id, scene.id, scene.scene_version
        source_item = make_ten_scene_seed()["groups"]["ones-group"]["item_ids"][0]

    provider = Provider()
    monkeypatch.setattr(
        student_routes,
        "create_studio_interaction_tutor_gateway",
        lambda gateway_session: ModelGateway(
            gateway_session,
            routes={ModelTask.TUTOR: ModelRoute("fixture", "make-ten-tutor")},
            providers={"fixture": provider},
        ),
    )
    client = _client(postgres_session_factory, subject="make-ten-api")
    try:
        transfer = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id),
                "base_scene_version": scene_version,
                "action_key": TRANSFER_ITEM_ACTION_KEY,
                "payload": {"item_id": source_item, "from_group_id": "ones-group", "to_group_id": "ten-frame"},
                "idempotency_key": "api-make-ten-transfer",
            },
        )
        assert transfer.status_code == 200
        assert transfer.json()["student_interaction_id"] is None

        with postgres_session_factory.begin() as session:
            snapshot = StudioStateService(session).runtime_state(runtime_id=runtime_id, student_id=student.id)["snapshot"]
            groups = snapshot["state_payload"]["ten_frame_group_transfer"]["groups"]
            ten_frame_item_ids = list(groups["ten-frame"]["item_ids"])
            ones_group_item_ids = list(groups["ones-group"]["item_ids"])
            current_scene = session.get(StudioScene, scene_id)
            assert current_scene is not None
            current_scene_version = current_scene.scene_version

        submit = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id),
                "base_scene_version": current_scene_version,
                "action_key": SUBMIT_CONFIGURATION_ACTION_KEY,
                "payload": {
                    "ten_frame_item_ids": ten_frame_item_ids,
                    "ones_group_item_ids": ones_group_item_ids,
                },
                "idempotency_key": "api-make-ten-submit",
            },
        )
        assert submit.status_code == 200
        interaction_id = submit.json()["student_interaction_id"]
        assert interaction_id and submit.json()["student_interaction_status"] == "PENDING"

        with postgres_session_factory.begin() as session:
            scene_after_submit = session.get(StudioScene, scene_id)
            interaction = session.get(StudioStudentInteraction, UUID(interaction_id))
            assert scene_after_submit is not None and interaction is not None
            assert interaction.status == "PENDING"
            submitted_scene_version = scene_after_submit.scene_version

        later_transfer = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id),
                "base_scene_version": submitted_scene_version,
                "action_key": TRANSFER_ITEM_ACTION_KEY,
                "payload": {
                    "item_id": ten_frame_item_ids[-1],
                    "from_group_id": "ten-frame",
                    "to_group_id": "ones-group",
                },
                "idempotency_key": "api-make-ten-record-only-after-submit",
            },
        )
        assert later_transfer.status_code == 200
        assert later_transfer.json()["student_interaction_id"] is None

        assert client.post(
            f"/api/v1/student/studio/{runtime_id}/interactions/{interaction_id}/turn/stream"
        ).status_code == 200
        assert provider.calls == 1
        with postgres_session_factory.begin() as session:
            messages = list(session.scalars(select(LearningMessage).where(LearningMessage.session_id == learning_session.id)))
            assert [(message.role, message.content) for message in messages] == [("tutor", "You made a full ten.")]
            interaction = session.get(StudioStudentInteraction, UUID(interaction_id))
            assert interaction is not None and interaction.status == "COMPLETED"
            assert interaction.tutor_message_id == messages[0].id
            runtime = session.get(StudioRuntime, runtime_id)
            assert runtime is not None and runtime.last_tutor_observation_sequence == 5
            assert session.scalar(select(func.count()).select_from(StudioEvent)) == 5
    finally:
        _clear_overrides()


def test_make_ten_activation_ignores_an_unrelated_accepted_scene_with_the_same_tutor_source(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    from services.studio.make_ten_activation import activate_make_ten_from_workspace_decision
    from services.studio.subjects.math_make_ten import ACTIVITY_KEY, make_ten_scene_seed

    with postgres_session_factory.begin() as session:
        student = _student(session, "make-ten-activation-unrelated")
        learning_session = _learning_session(session, student)
        source_segment, source_message = _tutor_source(session, learning_session)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        unrelated = _unrelated_accepted_scene(
            runtime_id=runtime.id,
            student=student,
            learning_session=learning_session,
            source_segment_id=source_segment.id,
            source_message_id=source_message.id,
        )
        session.add(unrelated)
        session.flush()

        activated = activate_make_ten_from_workspace_decision(
            session,
            learning_session=learning_session,
            source_tutor_message=source_message,
            source_segment_id=source_segment.id,
            workspace_audit=_make_ten_workspace_audit(),
        )

        assert activated is not None
        assert activated.id != unrelated.id
        assert activated.activity_key == ACTIVITY_KEY
        assert unrelated.status == "ACCEPTED"

        transfer = service.append_event(
            _transfer_command(
                runtime_id=runtime.id,
                student=student,
                learning_session=learning_session,
                scene=activated,
                item_id=make_ten_scene_seed()["groups"]["ones-group"]["item_ids"][0],
                idempotency_key="activation-reuse-preserves-progress",
            )
        )
        progressed_scene_version = transfer.scene.scene_version if transfer.scene is not None else None
        progressed_groups = service.runtime_state(runtime_id=runtime.id, student_id=student.id)["snapshot"]["state_payload"][ACTIVITY_KEY]["groups"]

        repeated = activate_make_ten_from_workspace_decision(
            session,
            learning_session=learning_session,
            source_tutor_message=source_message,
            source_segment_id=source_segment.id,
            workspace_audit=_make_ten_workspace_audit(),
        )

        assert repeated is not None and repeated.id == activated.id
        assert repeated.scene_version == progressed_scene_version
        assert service.runtime_state(runtime_id=runtime.id, student_id=student.id)["snapshot"]["state_payload"][ACTIVITY_KEY]["groups"] == progressed_groups
        assert session.scalar(select(func.count()).select_from(StudioScene)) == 2


def test_make_ten_activation_selects_the_one_exact_accepted_scene_among_multiple_sources(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    from services.studio.make_ten_activation import activate_make_ten_from_workspace_decision

    with postgres_session_factory.begin() as session:
        student = _student(session, "make-ten-activation-multiple")
        learning_session = _learning_session(session, student)
        source_segment, source_message = _tutor_source(session, learning_session)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        exact = service.accept_scene(
            _make_ten_scene_command(
                student,
                learning_session,
                source_segment_id=source_segment.id,
                source_message_id=source_message.id,
            )
        )
        unrelated = _unrelated_accepted_scene(
            runtime_id=runtime.id,
            student=student,
            learning_session=learning_session,
            source_segment_id=source_segment.id,
            source_message_id=source_message.id,
        )
        session.add(unrelated)
        session.flush()

        activated = activate_make_ten_from_workspace_decision(
            session,
            learning_session=learning_session,
            source_tutor_message=source_message,
            source_segment_id=source_segment.id,
            workspace_audit=_make_ten_workspace_audit(),
        )

        assert activated is not None and activated.id == exact.id
        assert activated.status == "ACTIVE"
        assert unrelated.status == "ACCEPTED"
        assert session.scalar(select(func.count()).select_from(StudioScene)) == 2


def test_normal_tutor_turn_activates_only_the_exact_persisted_make_ten_decision(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    from services.platform.db.models import ModelTask

    class Provider:
        def stream(self, route: ModelRoute, payload: dict[str, object]):
            del route, payload
            yield StreamDelta("Let us make a full ten.")
            yield StreamComplete(
                ModelResult(
                    output={
                        "text": "Let us make a full ten.",
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
                        "workspace_intent": _intent().model_dump(mode="json"),
                    }
                )
            )

    with postgres_session_factory.begin() as session:
        student = _student(session, "make-ten-normal-tutor")
        learning_session = _learning_session(session, student)
        student_id, learning_session_id = student.id, learning_session.id
    with postgres_session_factory.begin() as session:
        learning_session = session.get(LearningSession, learning_session_id)
        assert learning_session is not None
        runtime = TutorRuntime(
            session,
            context_builder=TutorContextBuilder(session, retrieval_service=RetrievalService(session)),
            safety_policy=SafetyPolicyService(session),
            gateway=ModelGateway(
                session,
                routes={ModelTask.TUTOR: ModelRoute("fixture", "make-ten-normal-tutor")},
                providers={"fixture": Provider()},
            ),
        )
        list(runtime.stream_turn(learning_session=learning_session, question="Can we make ten?"))

    with postgres_session_factory.begin() as session:
        scene = session.scalar(select(StudioScene).where(StudioScene.learning_session_id == learning_session_id))
        tutor_message = session.scalar(
            select(LearningMessage)
            .where(LearningMessage.session_id == learning_session_id, LearningMessage.role == "tutor")
        )
        assert scene is not None and tutor_message is not None
        assert scene.status == "ACTIVE"
        assert scene.source_message_id == tutor_message.id
        assert scene.source_segment_id == tutor_message.segment_id
        assert scene.student_id == student_id
        assert scene.activity_key == "ten_frame_group_transfer"
        assert session.scalar(select(func.count()).select_from(StudioStudentInteraction)) == 0
