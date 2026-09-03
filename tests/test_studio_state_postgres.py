"""PostgreSQL contracts for the durable, subject-agnostic Studio state foundation."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import UUID, uuid4

import pytest
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    AIExecution,
    CandidateEvent,
    CurrentLearningState,
    LearningEvent,
    LearningEvidence,
    LearningMessage,
    LearningSegment,
    LearningSession,
    ModelTask,
    PersonalFact,
    Student,
    User,
    StudioRuntime,
    StudioEvent,
)
from services.studio.contracts import (
    AppendStudioEventCommand,
    CreateCanvasSpecialistRunCommand,
    CreateSceneCommand,
    CreateTutorObservationCommand,
    StudioActor,
    StudioEventResultStatus,
)
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION, empty_snapshot, reduce_snapshot
from services.studio.service import (
    IdempotencyConflict,
    InvalidStudioLineage,
    StaleSceneVersion,
    StudioStateService,
    StudioStateError,
    UnknownStudioEvent,
)
from services.studio.subjects.contracts import (
    AccessibilityContract,
    ActivityActionContract,
    ActivityContract,
    InteractionPolicy,
    PayloadValidatorContract,
    ReducerContract,
    RendererContract,
    SubjectCapabilityProfile,
    ReducedMotionPolicy,
    SemanticValidationPolicy,
    ValidationResult,
    ValidationStatus,
    ValidatorContract,
)
from services.studio.subjects.registry import SubjectCapabilityRegistry
from services.studio.subjects import production_subject_registry


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Studio state contracts",
)


def _fixture_payload(payload: dict[str, object]) -> None:
    if (set(payload) == {"value"} and isinstance(payload["value"], int)) or (
        set(payload) == {"label"} and isinstance(payload["label"], str)
    ):
        return
    raise ValueError("fixture subject payload requires one bounded typed value")


def _fixture_reducer(snapshot: dict[str, object], event: object) -> dict[str, object]:
    from copy import deepcopy

    from services.studio.reducer import ReducerEvent

    assert isinstance(event, ReducerEvent)
    next_snapshot = deepcopy(snapshot)
    next_snapshot["latest_event_sequence"] = event.sequence
    return next_snapshot


def _fixture_semantic_validator(payload: dict[str, object]) -> ValidationResult:
    return ValidationResult(
        ValidationStatus.INVALID if payload["value"] == 0 else ValidationStatus.VALID,
        feedback_code="fixture-invalid" if payload["value"] == 0 else "fixture-valid",
    )


def _studio_test_registry() -> SubjectCapabilityRegistry:
    access = AccessibilityContract("buttons", "required", "supported", "bidirectional", "text", "safe-text", ReducedMotionPolicy.NO_MOTION)
    actions = (
        ActivityActionContract(
            "fixture.record", "fixture.recorded", "fixture-event-v1", "fixture-payload-v1", "fixture-payload", InteractionPolicy.RECORD_ONLY, SemanticValidationPolicy.NONE
        ),
        ActivityActionContract(
            "fixture.submit", "fixture.step_submitted", "fixture-event-v1", "fixture-payload-v1", "fixture-payload", InteractionPolicy.TUTOR_TRIGGERING, SemanticValidationPolicy.REQUIRED, "fixture-submit", "fixture-semantic", "1"
        ),
    )
    profile = SubjectCapabilityProfile(
        subject_key="MATH", profile_version="fixture-v1", supported_grade_scope=(), concept_namespace="fixture.math",
        tutor_guidance_fragment="fixture", grounding_policy_key="none", locale_policy_key="independent",
        deterministic_fallback="safe-text", canvas_specialist_profile_key=None,
        renderers=(RendererContract("native-react-svg", "1", "MATH", ("generic-workspace", "another-workspace"), "scene-v1", True, tuple(a.action_key for a in actions), (), "fixture", access, False, False, False, "TEST_ONLY"),),
        payload_validators=(PayloadValidatorContract("fixture-payload", "scene-v1", _fixture_payload), PayloadValidatorContract("fixture-payload", "fixture-payload-v1", _fixture_payload)),
        validators=(ValidatorContract("fixture-semantic", "1", _fixture_semantic_validator),),
        reducers=(ReducerContract("fixture-reducer", "1", _fixture_reducer),),
        activities=tuple(ActivityContract(key, "activity-v1", "MATH", "fixture.math", "native-react-svg", "1", "scene-v1", "fixture-payload", actions, "fixture", "bounded", (), "safe-text", access, "fixture-reducer", "1") for key in ("generic-workspace", "another-workspace")),
    )
    return SubjectCapabilityRegistry((profile,))


@pytest.fixture(autouse=True)
def _use_test_only_subject_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run accepted Core persistence tests through a test-only capability, never a production activity."""

    original_init = StudioStateService.__init__

    def configured_init(self: StudioStateService, session: Session, *, subject_registry=None) -> None:
        original_init(self, session, subject_registry=subject_registry or _studio_test_registry())

    monkeypatch.setattr(StudioStateService, "__init__", configured_init)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE studio_canvas_specialist_runs, studio_tutor_observations, "
                "studio_student_interactions, studio_events, studio_snapshots, studio_scenes, "
                "studio_runtimes, learning_messages, learning_segments, learning_sessions, "
                "candidate_events, learning_evidence, learning_events, current_learning_states, "
                "personal_facts, ai_executions, students, users CASCADE"
            )
        )
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _student(session: Session, suffix: str) -> Student:
    user = User(
        identity_provider="fixture",
        external_subject=f"studio-{suffix}-{uuid4().hex}",
        role="STUDENT",
    )
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name=suffix)
    session.add(student)
    session.flush()
    return student


def _session(session: Session, student: Student) -> LearningSession:
    learning_session = LearningSession(student_id=student.id, subject="MATH")
    session.add(learning_session)
    session.flush()
    return learning_session


def _scene_command(student: Student, learning_session: LearningSession, **overrides: object) -> CreateSceneCommand:
    values: dict[str, object] = {
        "student_id": student.id,
        "learning_session_id": learning_session.id,
        "subject_key": "MATH",
        "subject_profile_version": "fixture-v1",
        "concept_keys": ("fractions",),
        "activity_key": "generic-workspace",
        "artifact_type": "interactive-workspace",
        "renderer_key": "native-react-svg",
        "renderer_version": "1",
        "activity_contract_version": "activity-v1",
        "payload_schema_version": "scene-v1",
        "seed_payload": {"label": "A bounded scene seed"},
        "accessibility_payload": {"summary": "A generic learning workspace"},
        "locale": "en",
        "direction": "ltr",
    }
    values.update(overrides)
    return CreateSceneCommand(**values)  # type: ignore[arg-type]


def _append_command(
    runtime_id: UUID,
    student: Student,
    learning_session: LearningSession,
    *,
    event_kind: str = "studio.scene.activated",
    scene_id: UUID | None = None,
    base_scene_version: int | None = None,
    idempotency_key: str | None = None,
    payload: dict[str, object] | None = None,
    actor: StudioActor = StudioActor.SYSTEM,
    action_key: str | None = None,
    result_status: StudioEventResultStatus | str = StudioEventResultStatus.ACCEPTED,
    create_student_interaction: bool = False,
    source_message_id: UUID | None = None,
    source_segment_id: UUID | None = None,
) -> AppendStudioEventCommand:
    if create_student_interaction and event_kind == "studio.scene.activated":
        event_kind = "fixture.submit"
    if create_student_interaction and actor is StudioActor.SYSTEM:
        actor = StudioActor.STUDENT
    if not event_kind.startswith("studio.") and action_key is None:
        action_key = {"fixture.record": "fixture.record", "fixture.submit": "fixture.submit"}.get(event_kind)
    is_core = event_kind.startswith("studio.")
    return AppendStudioEventCommand(
        runtime_id=runtime_id,
        student_id=student.id,
        learning_session_id=learning_session.id,
        event_kind=event_kind if is_core else None,
        action_key=action_key,
        event_schema_version=CORE_EVENT_SCHEMA_VERSION if is_core else None,
        actor=actor,
        payload_schema_version="studio-event-payload-v1" if is_core else "fixture-payload-v1",
        payload=payload or ({} if is_core else {"value": 1}),
        scene_id=scene_id,
        base_scene_version=base_scene_version,
        idempotency_key=idempotency_key or f"event-{uuid4().hex}",
        result_status=result_status,
        source_message_id=source_message_id,
        source_segment_id=source_segment_id,
    )


def _runtime_scene(
    factory: sessionmaker[Session],
) -> tuple[UUID, UUID, UUID, UUID]:
    with factory.begin() as session:
        student = _student(session, "primary")
        learning_session = _session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(
            student_id=student.id, learning_session_id=learning_session.id
        )
        scene = service.accept_scene(_scene_command(student, learning_session))
        return student.id, learning_session.id, runtime.id, scene.id


def test_schema_inventory_includes_only_studio_foundation_tables_and_indexes() -> None:
    inspector = inspect(create_engine(normalize_database_url(os.environ["DATABASE_URL"])))
    tables = set(inspector.get_table_names())
    assert {
        "studio_runtimes",
        "studio_scenes",
        "studio_events",
        "studio_snapshots",
        "studio_student_interactions",
        "studio_tutor_observations",
        "studio_canvas_specialist_runs",
    }.issubset(tables)
    assert {index["name"] for index in inspector.get_indexes("studio_events")} >= {
        "ix_studio_events_runtime_sequence",
        "ix_studio_events_scene_sequence",
        "ix_studio_events_runtime_since_tutor_watermark",
    }
    result_status_constraint = {
        check["name"]: check["sqltext"] for check in inspector.get_check_constraints("studio_events")
    }
    reflected_result_status = result_status_constraint["ck_studio_events_result_status"]
    assert "result_status" in reflected_result_status
    assert "ACCEPTED" in reflected_result_status


def test_unregistered_production_scene_rejects_before_scene_event_or_snapshot_mutation(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Catch a generic Scene path that bypasses the production Subject Capability Registry."""

    with postgres_session_factory.begin() as session:
        student = _student(session, "production-capability-rejection")
        learning_session = _session(session, student)
        service = StudioStateService(session, subject_registry=production_subject_registry())
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        before = service.runtime_state(runtime_id=runtime.id, student_id=student.id)
        before_counts = (
            session.scalar(select(func.count()).select_from(StudioEvent)),
            session.scalar(select(func.count()).select_from(StudioRuntime)),
        )

        with pytest.raises(StudioStateError, match="Unsupported Subject profile"):
            service.accept_scene(_scene_command(student, learning_session))

        assert service.runtime_state(runtime_id=runtime.id, student_id=student.id) == before
        assert (
            session.scalar(select(func.count()).select_from(StudioEvent)),
            session.scalar(select(func.count()).select_from(StudioRuntime)),
        ) == before_counts


def test_runtime_is_one_per_session_and_student_scoped(postgres_session_factory: sessionmaker[Session]) -> None:
    with postgres_session_factory.begin() as session:
        student = _student(session, "runtime")
        learning_session = _session(session, student)
        service = StudioStateService(session)
        first = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        second = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        assert second.id == first.id
        assert first.latest_event_sequence == 0
        assert first.last_tutor_observation_sequence == 0

        other = _student(session, "wrong-owner")
        with pytest.raises(InvalidStudioLineage):
            service.get_or_create_runtime(student_id=other.id, learning_session_id=learning_session.id)


def test_result_status_invalid_direct_database_write_is_rejected(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    student_id, session_id, runtime_id, _scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        session.add(
            StudioEvent(
                studio_runtime_id=runtime_id,
                student_id=student.id,
                learning_session_id=learning_session.id,
                sequence=2,
                actor=StudioActor.SYSTEM.value,
                event_kind="fixture.record",
                event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                command_fingerprint="0" * 64,
                payload_schema_version="studio-event-payload-v1",
                payload={},
                result_status="INVALID",
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_result_status_application_contract_accepts_only_accepted(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    student_id, session_id, runtime_id, _scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        service = StudioStateService(session)
        accepted = service.append_event(
            _append_command(
                runtime_id,
                student,
                learning_session,
                event_kind="studio.runtime.initialized",
                result_status=StudioEventResultStatus.ACCEPTED,
            )
        )
        assert accepted.event.result_status == StudioEventResultStatus.ACCEPTED.value
        before = service.runtime_state(runtime_id=runtime_id, student_id=student.id)
        with pytest.raises(StudioStateError, match="result status"):
            service.append_event(
                _append_command(
                    runtime_id,
                    student,
                    learning_session,
                    event_kind="studio.runtime.initialized",
                    result_status="INVALID",
                )
            )
        assert service.runtime_state(runtime_id=runtime_id, student_id=student.id) == before


def test_database_enforces_runtime_session_student_lineage(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    try:
        runtime_foreign_keys = {
            foreign_key["name"]: (foreign_key["constrained_columns"], foreign_key["referred_table"], foreign_key["referred_columns"])
            for foreign_key in inspect(engine).get_foreign_keys("studio_runtimes")
        }
        assert runtime_foreign_keys["fk_studio_runtimes_session_student"] == (
            ["learning_session_id", "student_id"],
            "learning_sessions",
            ["id", "student_id"],
        )
        assert runtime_foreign_keys["fk_studio_runtimes_active_segment_session"] == (
            ["active_segment_id", "learning_session_id"],
            "learning_segments",
            ["id", "session_id"],
        )
        for table_name, constraint_name in (
            ("studio_events", "fk_studio_events_runtime_session_student"),
            ("studio_student_interactions", "fk_studio_interactions_runtime_session_student"),
        ):
            foreign_keys = {
                foreign_key["name"]: (
                    foreign_key["constrained_columns"],
                    foreign_key["referred_table"],
                    foreign_key["referred_columns"],
                )
                for foreign_key in inspect(engine).get_foreign_keys(table_name)
            }
            assert foreign_keys[constraint_name] == (
                ["studio_runtime_id", "student_id", "learning_session_id"],
                "studio_runtimes",
                ["id", "student_id", "learning_session_id"],
            )
        event_foreign_keys = {
            foreign_key["name"]: (
                foreign_key["constrained_columns"],
                foreign_key["referred_table"],
                foreign_key["referred_columns"],
            )
            for foreign_key in inspect(engine).get_foreign_keys("studio_events")
        }
        assert event_foreign_keys["fk_studio_events_causal_runtime_student"] == (
            ["causal_event_id", "studio_runtime_id", "student_id"],
            "studio_events",
            ["id", "studio_runtime_id", "student_id"],
        )
        source_constraints = (
            ("studio_scenes", "fk_studio_scenes_source_segment_session", "source_segment_id"),
            ("studio_scenes", "fk_studio_scenes_source_message_session", "source_message_id"),
            ("studio_events", "fk_studio_events_segment_session", "segment_id"),
            ("studio_events", "fk_studio_events_source_message_session", "source_message_id"),
            ("studio_canvas_specialist_runs", "fk_studio_specialist_runs_source_message_session", "source_message_id"),
        )
        for table_name, constraint_name, source_column in source_constraints:
            foreign_keys = {
                foreign_key["name"]: (
                    foreign_key["constrained_columns"],
                    foreign_key["referred_columns"],
                )
                for foreign_key in inspect(engine).get_foreign_keys(table_name)
            }
            assert foreign_keys[constraint_name] == (
                [source_column, "learning_session_id"],
                ["id", "session_id"],
            )
    finally:
        engine.dispose()

    with postgres_session_factory.begin() as session:
        first_student = _student(session, "runtime-lineage-first")
        second_student = _student(session, "runtime-lineage-second")
        second_session = _session(session, second_student)
        with session.begin_nested():
            session.add(
                StudioRuntime(
                    student_id=first_student.id,
                    learning_session_id=second_session.id,
                )
            )
            with pytest.raises(IntegrityError):
                session.flush()


def test_scene_lifecycle_has_one_database_backstopped_active_scene(postgres_session_factory: sessionmaker[Session]) -> None:
    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        service = StudioStateService(session)
        accepted = service.append_event(
            _append_command(runtime_id, student, learning_session, scene_id=scene_id, base_scene_version=1)
        )
        assert accepted.scene is not None and accepted.scene.status == "ACTIVE"
        second = service.accept_scene(_scene_command(student, learning_session, activity_key="another-workspace"))
        with pytest.raises(ValueError, match="active Scene"):
            service.append_event(
                _append_command(runtime_id, student, learning_session, scene_id=second.id, base_scene_version=1)
            )
        archived = service.append_event(
            _append_command(
                runtime_id,
                student,
                learning_session,
                event_kind="studio.scene.status_changed",
                scene_id=scene_id,
                base_scene_version=accepted.scene.scene_version,
                payload={"status": "ARCHIVED"},
            )
        )
        assert archived.scene is not None and archived.scene.status == "ARCHIVED"


def test_append_updates_event_scene_and_snapshot_deterministically(postgres_session_factory: sessionmaker[Session]) -> None:
    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        service = StudioStateService(session)
        first = service.append_event(
            _append_command(runtime_id, student, learning_session, scene_id=scene_id, base_scene_version=1)
        )
        assert first.event.sequence == 2
        assert first.snapshot.latest_event_sequence == 2
        assert first.scene is not None and first.scene.scene_version == 2
        with pytest.raises(UnknownStudioEvent):
            service.append_event(
                _append_command(
                    runtime_id,
                    student,
                    learning_session,
                    event_kind="studio.scene.state_transition",
                    scene_id=scene_id,
                    base_scene_version=2,
                    payload={"transition_key": "focus-step", "state": {"step_key": "one"}},
                )
            )
        assert first.snapshot.state_payload == {
            "scene_seed": {"label": "A bounded scene seed"},
            "scene_status": "ACTIVE",
        }
        with pytest.raises(StudioStateError, match="studio.recorded"):
            service.append_event(
                _append_command(
                    runtime_id,
                    student,
                    learning_session,
                    event_kind="studio.recorded",
                    payload={"activity_state": "bypass"},
                )
            )
        rebuilt = service.rebuild_snapshot(runtime_id=runtime_id, student_id=student.id)
        assert rebuilt == service.snapshot_projection(first.snapshot)


def test_subject_event_persists_action_key_separately_from_event_kind_and_core_keeps_null(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Catch inferred action identity or a schema that forbids Core lifecycle NULL action keys."""

    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        service = StudioStateService(session)

        subject_append = service.append_event(
            _append_command(
                runtime_id,
                student,
                learning_session,
                event_kind="fixture.submit",
                action_key="fixture.submit",
                actor=StudioActor.STUDENT,
                scene_id=scene_id,
                base_scene_version=1,
            )
        )
        core_append = service.append_event(
            _append_command(
                runtime_id,
                student,
                learning_session,
                event_kind="studio.runtime.initialized",
                action_key=None,
            )
        )

        assert subject_append.event.action_key == "fixture.submit"
        assert subject_append.event.event_kind == "fixture.step_submitted"
        assert core_append.event.action_key is None


def test_idempotent_replay_and_conflict_leave_state_unchanged(postgres_session_factory: sessionmaker[Session]) -> None:
    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        service = StudioStateService(session)
        command = _append_command(
            runtime_id,
            student,
            learning_session,
            scene_id=scene_id,
            base_scene_version=1,
            idempotency_key="activate-once",
            create_student_interaction=True,
        )
        first = service.append_event(command)
        replay = service.append_event(command)
        assert replay.replayed is True and replay.event.id == first.event.id
        assert session.scalar(select(func.count()).select_from(first.event.__class__)) == 2
        assert session.scalar(select(func.count()).select_from(first.interaction.__class__)) == 1
        with pytest.raises(IdempotencyConflict):
            service.append_event(
                _append_command(
                    runtime_id,
                    student,
                    learning_session,
                    scene_id=scene_id,
                    base_scene_version=2,
                    idempotency_key="activate-once",
                    payload={"changed": True},
                )
            )
        assert session.scalar(select(func.count()).select_from(first.event.__class__)) == 2
        with pytest.raises(IdempotencyConflict):
            service.append_event(
                _append_command(
                    runtime_id,
                    student,
                    learning_session,
                    scene_id=scene_id,
                    base_scene_version=2,
                    idempotency_key="activate-once",
                    event_kind="fixture.record",
                    action_key="fixture.record",
                )
            )
        assert session.scalar(select(func.count()).select_from(first.event.__class__)) == 2


def test_stale_unknown_and_oversized_event_leave_no_partial_write(postgres_session_factory: sessionmaker[Session]) -> None:
    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        service = StudioStateService(session)
        before = service.runtime_state(runtime_id=runtime_id, student_id=student.id)
        with pytest.raises(StaleSceneVersion):
            service.append_event(
                _append_command(runtime_id, student, learning_session, scene_id=scene_id, base_scene_version=99)
            )
        with pytest.raises(StudioStateError, match="Unsupported Activity action"):
            service.append_event(
                _append_command(
                    runtime_id,
                    student,
                    learning_session,
                    event_kind="math.fraction.partitioned",
                    action_key="math.fraction.partitioned",
                    scene_id=scene_id,
                    base_scene_version=1,
                )
            )
        with pytest.raises(ValueError, match="capacity"):
            service.append_event(
                _append_command(
                    runtime_id,
                    student,
                    learning_session,
                    scene_id=scene_id,
                    base_scene_version=1,
                    payload={"text": "x" * 20_000},
                )
            )
        after = service.runtime_state(runtime_id=runtime_id, student_id=student.id)
        assert after == before


def test_semantic_invalid_student_attempt_persists_bounded_result_and_one_interaction(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Catch rejection of a wrong but structurally valid Student action, or unbounded result persistence."""

    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        result = StudioStateService(session).append_event(
            _append_command(
                runtime_id,
                student,
                learning_session,
                event_kind="fixture.submit",
                action_key="fixture.submit",
                actor=StudioActor.STUDENT,
                scene_id=scene_id,
                base_scene_version=1,
                payload={"value": 0},
            )
        )

        assert result.event.action_key == "fixture.submit"
        assert result.event.event_kind == "fixture.step_submitted"
        assert result.event.result_status == "ACCEPTED"
        assert result.event.payload == {
            "action": {"value": 0},
            "validation": {
                "status": "INVALID",
                "feedback_code": "fixture-invalid",
                "next_action_keys": [],
            },
        }
        assert result.interaction is not None
        assert session.scalar(select(func.count()).select_from(result.interaction.__class__)) == 1


def test_scene_capacity_and_injected_snapshot_failure_roll_back_atomically(
    postgres_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    with postgres_session_factory.begin() as session:
        student = _student(session, "rollback")
        learning_session = _session(session, student)
        service = StudioStateService(session)
        service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        with pytest.raises(ValueError, match="capacity"):
            service.accept_scene(_scene_command(student, learning_session, seed_payload={"x": "x" * 20_000}))
        scene = service.accept_scene(_scene_command(student, learning_session))
        runtime = service.runtime_state(
            runtime_id=service.get_or_create_runtime(
                student_id=student.id, learning_session_id=learning_session.id
            ).id,
            student_id=student.id,
        )
        monkeypatch.setattr(service, "_apply_snapshot", lambda *_: (_ for _ in ()).throw(RuntimeError("injected")))
        with pytest.raises(RuntimeError, match="injected"):
            service.append_event(
                _append_command(
                    service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id).id,
                    student,
                    learning_session,
                    scene_id=scene.id,
                    base_scene_version=1,
                )
            )
        assert service.runtime_state(
            runtime_id=service.get_or_create_runtime(
                student_id=student.id, learning_session_id=learning_session.id
            ).id,
            student_id=student.id,
        ) == runtime


def test_source_message_and_segment_cross_scope_are_rejected(postgres_session_factory: sessionmaker[Session]) -> None:
    with postgres_session_factory.begin() as session:
        primary = _student(session, "source-primary")
        other = _student(session, "source-other")
        learning_session = _session(session, primary)
        other_session = _session(session, other)
        runtime = StudioStateService(session).get_or_create_runtime(
            student_id=primary.id, learning_session_id=learning_session.id
        )
        other_segment = LearningSegment(session_id=other_session.id, sequence=1)
        other_message = LearningMessage(session_id=other_session.id, role="tutor", content="foreign")
        session.add_all([other_segment, other_message])
        session.flush()
        with pytest.raises(InvalidStudioLineage):
            StudioStateService(session).accept_scene(
                _scene_command(
                    primary,
                    learning_session,
                    source_segment_id=other_segment.id,
                    source_message_id=other_message.id,
                )
            )
        assert runtime.latest_event_sequence == 0


def test_student_interaction_and_intelligence_personal_facts_boundaries(postgres_session_factory: sessionmaker[Session]) -> None:
    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        service = StudioStateService(session)
        result = service.append_event(
            _append_command(
                runtime_id,
                student,
                learning_session,
                scene_id=scene_id,
                base_scene_version=1,
                create_student_interaction=True,
                actor=StudioActor.STUDENT,
            )
        )
        assert result.interaction is not None and result.interaction.status == "PENDING"
        assert session.scalar(select(func.count()).select_from(CandidateEvent)) == 0
        assert session.scalar(select(func.count()).select_from(LearningEvent)) == 0
        assert session.scalar(select(func.count()).select_from(LearningEvidence)) == 0
        assert session.scalar(select(func.count()).select_from(CurrentLearningState)) == 0
        assert session.scalar(select(func.count()).select_from(PersonalFact)) == 0


def test_observation_and_specialist_are_dormant_scoped_persistence_seams(postgres_session_factory: sessionmaker[Session]) -> None:
    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        service = StudioStateService(session)
        append = service.append_event(
            _append_command(
                runtime_id,
                student,
                learning_session,
                scene_id=scene_id,
                base_scene_version=1,
                create_student_interaction=True,
            )
        )
        observation = service.create_tutor_observation(
            CreateTutorObservationCommand(
                runtime_id=runtime_id,
                student_id=student.id,
                from_event_sequence=1,
                through_event_sequence=append.event.sequence,
                student_interaction_id=append.interaction.id if append.interaction else None,
            )
        )
        assert observation.status == "SELECTED"
        assert service.runtime_state(runtime_id=runtime_id, student_id=student.id)["last_tutor_observation_sequence"] == 0
        student_source_message = LearningMessage(
            session_id=learning_session.id,
            role="student",
            content="source turn",
        )
        session.add(student_source_message)
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
            source_message_id=student_source_message.id,
        )
        session.add(execution)
        session.flush()
        committed = service.advance_tutor_observation_watermark(
            observation_id=observation.id,
            student_id=student.id,
            ai_execution_id=execution.id,
            source_message_id=student_source_message.id,
        )
        assert committed.status == "COMMITTED"
        assert service.runtime_state(runtime_id=runtime_id, student_id=student.id)["last_tutor_observation_sequence"] == append.event.sequence

        source_message = LearningMessage(session_id=learning_session.id, role="tutor", content="source turn")
        session.add(source_message)
        session.flush()
        specialist = service.create_canvas_specialist_run(
            CreateCanvasSpecialistRunCommand(
                runtime_id=runtime_id,
                student_id=student.id,
                source_message_id=source_message.id,
                scene_id=scene_id,
                base_scene_version=append.scene.scene_version if append.scene else 2,
                subject_key="MATH",
                capability_profile_version="future-profile-v1",
                output_schema_version="canvas-output-v1",
            )
        )
        assert specialist.status == "PENDING"
        assert session.scalar(select(func.count()).select_from(AIExecution)) == 1


def test_observation_and_specialist_reject_cross_student_references(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        service = StudioStateService(session)
        append = service.append_event(
            _append_command(
                runtime_id, student, learning_session, scene_id=scene_id, base_scene_version=1, create_student_interaction=True
            )
        )
        other = _student(session, "observation-other")
        other_session = _session(session, other)
        other_runtime = service.get_or_create_runtime(student_id=other.id, learning_session_id=other_session.id)
        service.accept_scene(_scene_command(other, other_session))
        with pytest.raises(InvalidStudioLineage):
            service.create_tutor_observation(
                CreateTutorObservationCommand(
                    runtime_id=other_runtime.id,
                    student_id=other.id,
                    from_event_sequence=1,
                    through_event_sequence=1,
                    student_interaction_id=append.interaction.id if append.interaction else None,
                )
            )
        foreign_message = LearningMessage(session_id=other_session.id, role="tutor", content="foreign")
        session.add(foreign_message)
        session.flush()
        with pytest.raises(InvalidStudioLineage):
            service.create_canvas_specialist_run(
                CreateCanvasSpecialistRunCommand(
                    runtime_id=runtime_id,
                    student_id=student.id,
                    source_message_id=foreign_message.id,
                    scene_id=scene_id,
                    base_scene_version=append.scene.scene_version if append.scene else 2,
                    subject_key="MATH",
                    capability_profile_version="future-profile-v1",
                    output_schema_version="canvas-output-v1",
                )
            )


def test_runtime_append_is_postgres_concurrent_and_unrelated_runtimes_are_independent(
    postgres_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    first_student_id, first_session_id, first_runtime_id, first_scene_id = _runtime_scene(postgres_session_factory)
    second_student_id, second_session_id, second_runtime_id, second_scene_id = _runtime_scene(postgres_session_factory)

    def append(runtime_id: UUID, student_id: UUID, session_id: UUID, scene_id: UUID, key: str) -> int:
        with postgres_session_factory.begin() as session:
            student = session.get(Student, student_id)
            learning_session = session.get(LearningSession, session_id)
            assert student is not None and learning_session is not None
            result = StudioStateService(session).append_event(
                _append_command(
                    runtime_id,
                    student,
                    learning_session,
                        event_kind="studio.runtime.initialized",
                    idempotency_key=key,
                )
            )
            return result.event.sequence

    first_runtime_locked = Event()
    release_first_runtime = Event()
    same_runtime_lock_attempted = Event()
    unrelated_runtime_entered = Event()
    original_append_locked = StudioStateService._append_locked
    original_runtime_locked = StudioStateService._runtime_locked

    def track_competing_lock_attempt(
        service: StudioStateService,
        student_id: UUID,
        learning_session_id: UUID | None,
        *,
        runtime_id: UUID | None = None,
    ) -> StudioRuntime:
        if runtime_id == first_runtime_id and first_runtime_locked.is_set():
            same_runtime_lock_attempted.set()
        return original_runtime_locked(
            service,
            student_id,
            learning_session_id,
            runtime_id=runtime_id,
        )

    def hold_one_runtime_lock(
        service: StudioStateService,
        runtime: StudioRuntime,
        command: AppendStudioEventCommand,
    ):
        if runtime.id == first_runtime_id and not first_runtime_locked.is_set():
            first_runtime_locked.set()
            assert release_first_runtime.wait(timeout=5)
        if runtime.id == second_runtime_id:
            unrelated_runtime_entered.set()
        return original_append_locked(service, runtime, command)

    monkeypatch.setattr(StudioStateService, "_append_locked", hold_one_runtime_lock)
    monkeypatch.setattr(StudioStateService, "_runtime_locked", track_competing_lock_attempt)
    with ThreadPoolExecutor(max_workers=3) as executor:
        first = executor.submit(
            append,
            first_runtime_id,
            first_student_id,
            first_session_id,
            first_scene_id,
            "concurrent-first",
        )
        assert first_runtime_locked.wait(timeout=5)
        same_runtime = executor.submit(
            append,
            first_runtime_id,
            first_student_id,
            first_session_id,
            first_scene_id,
            "concurrent-second",
        )
        assert same_runtime_lock_attempted.wait(timeout=5)
        unrelated = executor.submit(
            append,
            second_runtime_id,
            second_student_id,
            second_session_id,
            second_scene_id,
            "unrelated",
        )
        assert unrelated_runtime_entered.wait(timeout=5)
        assert unrelated.result(timeout=5) == 2
        assert same_runtime.done() is False
        release_first_runtime.set()
        assert sorted((first.result(timeout=5), same_runtime.result(timeout=5))) == [2, 3]


def test_concurrent_identical_idempotency_key_persists_one_event(
    postgres_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    student_id, session_id, runtime_id, _scene_id = _runtime_scene(postgres_session_factory)
    first_runtime_locked = Event()
    release_first_runtime = Event()
    competing_lock_attempted = Event()
    original_append_locked = StudioStateService._append_locked
    original_runtime_locked = StudioStateService._runtime_locked
    target_runtime_id = runtime_id

    def track_competing_lock_attempt(
        service: StudioStateService,
        student_id: UUID,
        learning_session_id: UUID | None,
        *,
        runtime_id: UUID | None = None,
    ) -> StudioRuntime:
        if runtime_id == target_runtime_id and first_runtime_locked.is_set():
            competing_lock_attempted.set()
        return original_runtime_locked(
            service,
            student_id,
            learning_session_id,
            runtime_id=runtime_id,
        )

    def hold_first_runtime_lock(
        service: StudioStateService,
        runtime: StudioRuntime,
        command: AppendStudioEventCommand,
    ):
        if runtime.id == target_runtime_id and not first_runtime_locked.is_set():
            first_runtime_locked.set()
            assert release_first_runtime.wait(timeout=5)
        return original_append_locked(service, runtime, command)

    monkeypatch.setattr(StudioStateService, "_runtime_locked", track_competing_lock_attempt)
    monkeypatch.setattr(StudioStateService, "_append_locked", hold_first_runtime_lock)

    def append() -> tuple[UUID, int, bool]:
        with postgres_session_factory.begin() as session:
            student = session.get(Student, student_id)
            learning_session = session.get(LearningSession, session_id)
            assert student is not None and learning_session is not None
            result = StudioStateService(session).append_event(
                _append_command(
                    runtime_id,
                    student,
                    learning_session,
                        event_kind="studio.runtime.initialized",
                    idempotency_key="same-concurrent-key",
                )
            )
            return result.event.id, result.event.sequence, result.replayed

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(append)
        assert first_runtime_locked.wait(timeout=5)
        second = executor.submit(append)
        assert competing_lock_attempted.wait(timeout=5)
        release_first_runtime.set()
        outcomes = (first.result(timeout=5), second.result(timeout=5))

    assert len({outcome[0] for outcome in outcomes}) == 1
    assert {outcome[1] for outcome in outcomes} == {2}
    assert sorted(outcome[2] for outcome in outcomes) == [False, True]
    with postgres_session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(StudioEvent).where(StudioEvent.studio_runtime_id == runtime_id)
        ) == 2


def test_studio_migration_downgrade_and_reupgrade_round_trip_on_disposable_postgres() -> None:
    config = Config("alembic.ini")
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))

    def assert_result_status_constraint() -> None:
        checks = {check["name"]: check["sqltext"] for check in inspect(engine).get_check_constraints("studio_events")}
        reflected_result_status = checks["ck_studio_events_result_status"]
        assert "result_status" in reflected_result_status
        assert "ACCEPTED" in reflected_result_status

    try:
        alembic_command.downgrade(config, "a1d2e3f4b5c6")
        tables = set(inspect(engine).get_table_names())
        assert "studio_runtimes" not in tables
        factory = sessionmaker(engine, expire_on_commit=False)
        with factory.begin() as session:
            student = _student(session, "migration-preserved")
            learning_session = _session(session, student)
            message = LearningMessage(
                session_id=learning_session.id,
                role="student",
                content="pre-Studio history remains intact",
            )
            session.add(message)
            session.flush()
            expected_ids = (student.id, learning_session.id, message.id)
        alembic_command.upgrade(config, "head")
        tables = set(inspect(engine).get_table_names())
        assert "studio_runtimes" in tables
        assert_result_status_constraint()
        with factory() as session:
            student_id, learning_session_id, message_id = expected_ids
            assert session.get(Student, student_id) is not None
            restored_session = session.get(LearningSession, learning_session_id)
            restored_message = session.get(LearningMessage, message_id)
            assert restored_session is not None and restored_session.student_id == student_id
            assert restored_message is not None and restored_message.session_id == learning_session_id
            assert restored_message.content == "pre-Studio history remains intact"
        alembic_command.downgrade(config, "a1d2e3f4b5c6")
        alembic_command.upgrade(config, "head")
        assert_result_status_constraint()
    finally:
        alembic_command.upgrade(config, "head")
        engine.dispose()
