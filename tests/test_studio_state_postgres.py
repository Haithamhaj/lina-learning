"""PostgreSQL contracts for the durable, subject-agnostic Studio state foundation."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from uuid import UUID, uuid4

import pytest
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
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
    StudioScene,
    StudioEvent,
    StudioStudentInteraction,
    StudioTutorObservation,
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


class _RecordingStudioTutorProvider:
    """A Gateway-level fixture that records one internal Canvas Tutor call."""

    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        assert route.model == "fixture-tutor"
        self.payloads.append(payload)
        return ModelResult(
            output={"text": "Let us examine that step.", "workspace_intent": None},
            input_tokens=7,
            output_tokens=5,
        )


class _StreamingStudioTutorProvider(_RecordingStudioTutorProvider):
    """A real Gateway stream fixture; it never synthesizes route-level deltas."""

    def stream(self, route: ModelRoute, payload: dict[str, object]):  # type: ignore[no-untyped-def]
        result = self.execute(route, payload)
        yield StreamDelta("Let us ")
        yield StreamDelta("examine that step.")
        yield StreamComplete(result)


class _PausedStudioTutorProvider(_RecordingStudioTutorProvider):
    """Blocks provider work after admission so concurrent database work is observable."""

    def __init__(self) -> None:
        super().__init__()
        self.started = Event()
        self.release = Event()

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        self.started.set()
        assert self.release.wait(timeout=5)
        return super().execute(route, payload)


class _FailingStudioTutorProvider:
    """Exercises the real Gateway failure ledger without a live model call."""

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route, payload
        self.calls += 1
        raise RuntimeError("fixture provider failure")


class _MissingWorkspaceIntentProvider:
    """Models a malformed v9 result that must not silently become null."""

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route, payload
        return ModelResult(output={"text": "Malformed v9 fixture."})


def _studio_tutor_service(*, engine: object, provider: object):
    from services.studio.interactions import StudioInteractionTutorService

    return StudioInteractionTutorService(
        bind=engine,  # type: ignore[arg-type]
        gateway_factory=lambda gateway_session: ModelGateway(
            gateway_session,
            routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")},
            providers={"fixture": provider},  # type: ignore[dict-item]
        ),
        subject_registry=_studio_test_registry(),
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


def _triggering_interaction(
    factory: sessionmaker[Session],
    *,
    payload: dict[str, object] | None = None,
) -> tuple[UUID, UUID, UUID, UUID, UUID, object]:
    student_id, session_id, runtime_id, scene_id = _runtime_scene(factory)
    with factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        append = StudioStateService(session).append_event(
            _append_command(
                runtime_id,
                student,
                learning_session,
                scene_id=scene_id,
                base_scene_version=1,
                create_student_interaction=True,
                actor=StudioActor.STUDENT,
                payload=payload or {"value": 0},
            )
        )
        assert append.interaction is not None
        return student_id, session_id, runtime_id, scene_id, append.interaction.id, session.get_bind()


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


def test_pending_interaction_claim_is_owned_atomic_and_non_repeatable(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Only the owning Student may atomically claim one contract-created hand-off."""

    from services.studio.interactions import (  # noqa: PLC0415 - RED contract
        StudioInteractionAccessDenied,
        StudioInteractionService,
        StudioInteractionStateError,
    )

    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        interaction = StudioStateService(session).append_event(
            _append_command(
                runtime_id,
                student,
                learning_session,
                scene_id=scene_id,
                base_scene_version=1,
                create_student_interaction=True,
                actor=StudioActor.STUDENT,
            )
        ).interaction
        assert interaction is not None
        interaction_id = interaction.id

    with postgres_session_factory.begin() as session:
        claimed = StudioInteractionService(session).claim_pending(
            student_id=student_id,
            runtime_id=runtime_id,
            interaction_id=interaction_id,
        )
        assert claimed.status == "RUNNING"

    with postgres_session_factory.begin() as session:
        with pytest.raises(StudioInteractionStateError, match="not pending"):
            StudioInteractionService(session).claim_pending(
                student_id=student_id,
                runtime_id=runtime_id,
                interaction_id=interaction_id,
            )
        with pytest.raises(StudioInteractionAccessDenied):
            StudioInteractionService(session).claim_pending(
                student_id=uuid4(),
                runtime_id=runtime_id,
                interaction_id=interaction_id,
            )


def test_new_triggering_action_supersedes_a_running_interaction(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """A newer meaningful Canvas action wins without treating record-only events as a turn."""

    from services.studio.interactions import StudioInteractionService  # noqa: PLC0415 - RED contract

    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        state = StudioStateService(session)
        first = state.append_event(
            _append_command(
                runtime_id, student, learning_session, scene_id=scene_id, base_scene_version=1,
                create_student_interaction=True, actor=StudioActor.STUDENT,
            )
        )
        assert first.interaction is not None and first.scene is not None
        StudioInteractionService(session).claim_pending(
            student_id=student_id, runtime_id=runtime_id, interaction_id=first.interaction.id,
        )
        second = state.append_event(
            _append_command(
                runtime_id, student, learning_session, scene_id=scene_id,
                base_scene_version=first.scene.scene_version,
                create_student_interaction=True, actor=StudioActor.STUDENT,
            )
        )
        assert second.interaction is not None
        assert first.interaction.status == "SUPERSEDED"
        assert second.interaction.status == "PENDING"


def test_new_real_chat_input_supersedes_a_running_canvas_interaction(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """A later Chat Student message is the causal successor of Canvas generation."""

    from services.studio.interactions import StudioInteractionService

    student_id, session_id, runtime_id, _scene_id, interaction_id, _engine = _triggering_interaction(
        postgres_session_factory
    )
    with postgres_session_factory.begin() as session:
        StudioInteractionService(session).claim_pending(
            student_id=student_id, runtime_id=runtime_id, interaction_id=interaction_id
        )
        StudioInteractionService(session).supersede_running_for_new_chat_student_input(
            student_id=student_id,
            learning_session_id=session_id,
        )

    with postgres_session_factory.begin() as session:
        interaction = session.get(StudioStudentInteraction, interaction_id)
        assert interaction is not None and interaction.status == "SUPERSEDED"


def test_chat_terminal_guard_rejects_newer_triggering_canvas_but_not_record_only(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """The terminal guard consults durable triggering interactions, not all events."""

    from services.studio.interactions import StudioInteractionService, StudioInteractionStateError

    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        scene = session.get(StudioScene, scene_id)
        assert student is not None and learning_session is not None and scene is not None
        state = StudioStateService(session)
        state.append_event(
            _append_command(
                runtime_id, student, learning_session, scene_id=scene_id,
                base_scene_version=scene.scene_version, action_key="fixture.record",
                event_kind="fixture.record", actor=StudioActor.STUDENT, payload={"value": 1},
            )
        )
        StudioInteractionService(session).require_chat_terminal_current(
            student_id=student_id, learning_session_id=session_id, through_event_sequence=1,
        )
        scene = session.get(StudioScene, scene_id)
        assert scene is not None
        state.append_event(
            _append_command(
                runtime_id, student, learning_session, scene_id=scene_id,
                base_scene_version=scene.scene_version, create_student_interaction=True,
                actor=StudioActor.STUDENT, payload={"value": 2},
            )
        )
        with pytest.raises(StudioInteractionStateError, match="newer Canvas"):
            StudioInteractionService(session).require_chat_terminal_current(
                student_id=student_id, learning_session_id=session_id, through_event_sequence=2,
            )


def test_owned_canvas_interaction_executes_once_with_exact_gateway_lineage(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """A persisted trigger starts one internal Tutor execution without Chat side effects."""

    from services.studio.interactions import StudioInteractionTutorService  # noqa: PLC0415 - RED contract

    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        interaction = StudioStateService(session).append_event(
            _append_command(
                runtime_id,
                student,
                learning_session,
                scene_id=scene_id,
                base_scene_version=1,
                create_student_interaction=True,
                actor=StudioActor.STUDENT,
                payload={"value": 0},
            )
        ).interaction
        assert interaction is not None
        interaction_id = interaction.id
        engine = session.get_bind()

    provider = _RecordingStudioTutorProvider()

    def gateway_factory(gateway_session: Session) -> ModelGateway:
        return ModelGateway(
            gateway_session,
            routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")},
            providers={"fixture": provider},
        )

    result = StudioInteractionTutorService(
        bind=engine,
        gateway_factory=gateway_factory,
        subject_registry=_studio_test_registry(),
    ).execute(
        student_id=student_id,
        learning_session_id=session_id,
        runtime_id=runtime_id,
        interaction_id=interaction_id,
    )

    assert len(provider.payloads) == 1
    assert provider.payloads[0]["response_schema"]["name"] == "tutor_turn_v9"  # type: ignore[index]
    assert "question" not in provider.payloads[0]
    source = result.context.as_model_payload()["source"]
    assert source["turn_origin"] == "CANVAS_INTERACTION"
    assert source["interaction_kind"] == "fixture-submit"
    assert source["event"]["sequence"] == 2
    assert source["event"]["action_key"] == "fixture.submit"
    assert source["event"]["event_kind"] == "fixture.step_submitted"
    assert source["event"]["validation"]["status"] == "INVALID"
    assert source["event"]["action_payload"] == {"value": 0}

    with postgres_session_factory.begin() as session:
        execution = session.get(AIExecution, result.result.execution_id)
        interaction = session.get(StudioStudentInteraction, interaction_id)
        assert execution is not None
        assert execution.task == ModelTask.TUTOR.value
        assert execution.operation_type == "studio_interaction_tutor_turn"
        assert execution.operation_id == interaction_id
        assert execution.student_id == student_id
        assert execution.learning_session_id == session_id
        assert execution.source_message_id is None
        assert execution.success is True
        assert interaction is not None and interaction.status == "RUNNING"
        assert session.scalar(select(func.count()).select_from(LearningMessage)) == 0
        assert session.scalar(select(func.count()).select_from(CandidateEvent)) == 0
        assert session.scalar(select(func.count()).select_from(LearningEvent)) == 0
        assert session.scalar(select(func.count()).select_from(LearningEvidence)) == 0
        assert session.scalar(select(func.count()).select_from(CurrentLearningState)) == 0
        assert session.scalar(select(func.count()).select_from(PersonalFact)) == 0


def test_canvas_interaction_rejects_a_noncanonical_persisted_validation_envelope(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """A source mutation cannot reintroduce arbitrary validation metadata into Tutor context."""

    from services.studio.interactions import (  # noqa: PLC0415 - RED contract
        StudioInteractionSourceError,
        StudioInteractionTutorService,
    )

    student_id, session_id, runtime_id, scene_id = _runtime_scene(postgres_session_factory)
    with postgres_session_factory.begin() as session:
        student = session.get(Student, student_id)
        learning_session = session.get(LearningSession, session_id)
        assert student is not None and learning_session is not None
        interaction = StudioStateService(session).append_event(
            _append_command(
                runtime_id,
                student,
                learning_session,
                scene_id=scene_id,
                base_scene_version=1,
                create_student_interaction=True,
                actor=StudioActor.STUDENT,
                payload={"value": 0},
            )
        ).interaction
        assert interaction is not None
        event = session.get(StudioEvent, interaction.source_event_id)
        assert event is not None
        event.payload = {
            "action": {"value": 0},
            "validation": {
                "status": "INVALID",
                "feedback_code": "fixture-invalid",
                "next_action_keys": [],
                "metadata": {"unbounded": "must not reach the model"},
            },
        }
        interaction_id = interaction.id
        engine = session.get_bind()

    provider = _RecordingStudioTutorProvider()
    with pytest.raises(StudioInteractionSourceError, match="validation"):
        StudioInteractionTutorService(
            bind=engine,
            gateway_factory=lambda gateway_session: ModelGateway(
                gateway_session,
                routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")},
                providers={"fixture": provider},
            ),
            subject_registry=_studio_test_registry(),
        ).execute(
            student_id=student_id,
            learning_session_id=session_id,
            runtime_id=runtime_id,
            interaction_id=interaction_id,
        )
    assert provider.payloads == []
    with postgres_session_factory.begin() as session:
        interaction = session.get(StudioStudentInteraction, interaction_id)
        assert interaction is not None and interaction.status == "PENDING"
        assert session.scalar(select(func.count()).select_from(AIExecution)) == 0


def test_canvas_interaction_scope_rejection_preserves_pending_state_without_provider_execution(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Wrong trusted Student/session/runtime scope cannot claim or execute a Canvas interaction."""

    from services.studio.interactions import StudioInteractionAccessDenied, StudioInteractionSourceError

    student_id, session_id, runtime_id, _scene_id, interaction_id, engine = _triggering_interaction(
        postgres_session_factory
    )
    provider = _RecordingStudioTutorProvider()
    service = _studio_tutor_service(engine=engine, provider=provider)

    for rejected_scope in (
        {"student_id": uuid4()},
        {"learning_session_id": uuid4()},
        {"runtime_id": uuid4()},
    ):
        with pytest.raises(StudioInteractionAccessDenied):
            service.execute(
                student_id=rejected_scope.get("student_id", student_id),  # type: ignore[arg-type]
                learning_session_id=rejected_scope.get("learning_session_id", session_id),  # type: ignore[arg-type]
                runtime_id=rejected_scope.get("runtime_id", runtime_id),  # type: ignore[arg-type]
                interaction_id=interaction_id,
            )

    with postgres_session_factory.begin() as session:
        interaction = session.get(StudioStudentInteraction, interaction_id)
        assert interaction is not None
        source_event = session.get(StudioEvent, interaction.source_event_id)
        assert source_event is not None
        source_event.subject_key = "SCIENCE"
    with pytest.raises(StudioInteractionSourceError, match="does not match"):
        service.execute(
            student_id=student_id,
            learning_session_id=session_id,
            runtime_id=runtime_id,
            interaction_id=interaction_id,
        )

    assert provider.payloads == []
    with postgres_session_factory.begin() as session:
        interaction = session.get(StudioStudentInteraction, interaction_id)
        assert interaction is not None and interaction.status == "PENDING"
        assert session.scalar(select(func.count()).select_from(AIExecution)) == 0


def test_canvas_interaction_replay_refuses_a_second_provider_execution(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Only the admitted PENDING transition may initiate a primary Tutor call."""

    from services.studio.interactions import StudioInteractionStateError

    student_id, session_id, runtime_id, _scene_id, interaction_id, engine = _triggering_interaction(
        postgres_session_factory
    )
    provider = _RecordingStudioTutorProvider()
    service = _studio_tutor_service(engine=engine, provider=provider)
    service.execute(
        student_id=student_id,
        learning_session_id=session_id,
        runtime_id=runtime_id,
        interaction_id=interaction_id,
    )

    with pytest.raises(StudioInteractionStateError, match="not pending"):
        service.execute(
            student_id=student_id,
            learning_session_id=session_id,
            runtime_id=runtime_id,
            interaction_id=interaction_id,
        )

    assert len(provider.payloads) == 1
    with postgres_session_factory.begin() as session:
        assert session.scalar(select(func.count()).select_from(AIExecution)) == 1


def test_canvas_interaction_context_retains_its_source_below_the_tutor_watermark(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """The current interaction source is explicit, not selected from unseen Chat observation Events."""

    student_id, session_id, runtime_id, _scene_id, interaction_id, engine = _triggering_interaction(
        postgres_session_factory
    )
    with postgres_session_factory.begin() as session:
        runtime = session.get(StudioRuntime, runtime_id)
        assert runtime is not None
        runtime.last_tutor_observation_sequence = runtime.latest_event_sequence

    provider = _RecordingStudioTutorProvider()
    result = _studio_tutor_service(engine=engine, provider=provider).execute(
        student_id=student_id,
        learning_session_id=session_id,
        runtime_id=runtime_id,
        interaction_id=interaction_id,
    )

    assert result.context.as_model_payload()["source"]["event"]["sequence"] == 2
    assert result.context.as_model_payload()["workspace"]["last_tutor_observation_sequence"] == 2
    with postgres_session_factory.begin() as session:
        assert session.scalar(select(func.count()).select_from(StudioTutorObservation)) == 0
        runtime = session.get(StudioRuntime, runtime_id)
        assert runtime is not None and runtime.last_tutor_observation_sequence == 2


def test_canvas_selection_binds_its_exact_interaction_to_the_observation(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """A Canvas turn owns any unseen-range observation it selected."""

    from services.studio.tutor_context import select_studio_tutor_context  # noqa: PLC0415 - RED contract

    student_id, session_id, _runtime_id, _scene_id, interaction_id, engine = _triggering_interaction(
        postgres_session_factory
    )

    selection = select_studio_tutor_context(
        bind=engine,
        student_id=student_id,
        learning_session_id=session_id,
        student_interaction_id=interaction_id,
    )

    assert selection is not None
    assert selection.context.observation_id is not None
    with postgres_session_factory.begin() as session:
        observation = session.get(StudioTutorObservation, selection.context.observation_id)
        assert observation is not None
        assert observation.student_interaction_id == interaction_id


def test_canvas_stream_persists_one_real_tutor_message_then_finalizes(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Canvas delivery uses one Gateway stream, no fake Student message, and exact completion."""

    from services.studio.interactions import (
        StudioInteractionTutorService,
    )  # noqa: PLC0415 - RED contract

    student_id, session_id, runtime_id, _scene_id, interaction_id, engine = _triggering_interaction(
        postgres_session_factory
    )
    provider = _StreamingStudioTutorProvider()
    service = _studio_tutor_service(engine=engine, provider=provider)
    admission = service.admit(
        student_id=student_id,
        learning_session_id=session_id,
        runtime_id=runtime_id,
        interaction_id=interaction_id,
    )
    terminal = None
    deltas: list[str] = []
    for event in service.stream_admitted(admission=admission, student_id=student_id):
        if isinstance(event, StreamDelta):
            deltas.append(event.text)
        elif isinstance(event, StreamComplete):
            terminal = event.result
    assert terminal is not None
    turn = service.persist_canvas_turn(admission=admission, result=terminal, student_id=student_id)
    service.finalize_delivered_turn(admission=admission, turn=turn, student_id=student_id)

    assert deltas == ["Let us ", "examine that step."]
    assert len(provider.payloads) == 1
    provider_payload = provider.payloads[0]
    workspace = provider_payload["studio_workspace_context"]
    assert workspace["snapshot"]["sequence"] == 2
    assert [event["sequence"] for event in workspace["unseen_events"]] == [1, 2]
    assert provider_payload["studio_interaction_context"]["source"]["event"]["sequence"] == 2
    assert '"through_sequence": 2' in provider_payload["input"]
    with postgres_session_factory.begin() as session:
        interaction = session.get(StudioStudentInteraction, interaction_id)
        assert interaction is not None
        assert interaction.status == "COMPLETED"
        assert interaction.tutor_message_id == turn.message_id
        assert interaction.ai_execution_id == terminal.execution_id
        tutor_message = session.get(LearningMessage, turn.message_id)
        assert tutor_message is not None and tutor_message.role == "tutor"
        assert tutor_message.payload["turn_origin"] == "STUDIO_INTERACTION"
        assert tutor_message.payload["student_interaction_id"] == str(interaction_id)
        assert tutor_message.payload["source_studio_event_id"] == str(interaction.source_event_id)
        assert session.scalar(select(func.count()).select_from(LearningMessage).where(LearningMessage.role == "student")) == 0
        assert session.scalar(select(func.count()).select_from(CandidateEvent)) == 0
        assert session.scalar(select(func.count()).select_from(LearningEvent)) == 0
        assert session.scalar(select(func.count()).select_from(LearningEvidence)) == 0
        observation = session.get(StudioTutorObservation, admission.observation_id)
        assert observation is not None
        assert observation.status == "COMMITTED"
        assert observation.student_interaction_id == interaction_id


def test_canvas_terminal_waits_on_learning_session_before_locking_runtime(
    postgres_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches Canvas terminal lock inversion against a Chat Student admission."""

    from services.studio.interactions import StudioInteractionTutorService

    student_id, session_id, runtime_id, _scene_id, interaction_id, engine = _triggering_interaction(
        postgres_session_factory
    )
    provider = _StreamingStudioTutorProvider()
    service = _studio_tutor_service(engine=engine, provider=provider)
    admission = service.admit(
        student_id=student_id,
        learning_session_id=session_id,
        runtime_id=runtime_id,
        interaction_id=interaction_id,
    )
    terminal = None
    for event in service.stream_admitted(admission=admission, student_id=student_id):
        if isinstance(event, StreamComplete):
            terminal = event.result
    assert terminal is not None
    runtime_locked_before_session = Event()
    original_verify = StudioInteractionTutorService._verify_execution_provenance_in_session

    def observe_runtime_lock(session: Session, **kwargs: object) -> None:
        runtime_locked_before_session.set()
        original_verify(session, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        StudioInteractionTutorService,
        "_verify_execution_provenance_in_session",
        staticmethod(observe_runtime_lock),
    )

    def persist() -> object:
        return service.persist_canvas_turn(admission=admission, result=terminal, student_id=student_id)

    with postgres_session_factory() as chat_session:
        transaction = chat_session.begin()
        try:
            chat_session.execute(
                select(LearningSession)
                .where(LearningSession.id == session_id)
                .with_for_update()
            ).scalar_one()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(persist)
                observed = runtime_locked_before_session.wait(timeout=0.5)
                transaction.commit()
                future.result(timeout=5)
        finally:
            if transaction.is_active:
                transaction.rollback()

    assert observed is False


def test_canvas_provider_failure_keeps_interaction_nonfinal_and_records_gateway_failure(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """A failed provider attempt is durable operational provenance, never a completed Canvas turn."""

    student_id, session_id, runtime_id, _scene_id, interaction_id, engine = _triggering_interaction(
        postgres_session_factory
    )
    provider = _FailingStudioTutorProvider()
    with pytest.raises(RuntimeError, match="fixture provider failure"):
        _studio_tutor_service(engine=engine, provider=provider).execute(
            student_id=student_id,
            learning_session_id=session_id,
            runtime_id=runtime_id,
            interaction_id=interaction_id,
        )

    assert provider.calls == 1
    with postgres_session_factory.begin() as session:
        interaction = session.get(StudioStudentInteraction, interaction_id)
        execution = session.scalar(
            select(AIExecution).where(AIExecution.operation_id == interaction_id)
        )
        assert interaction is not None and interaction.status == "RUNNING"
        assert interaction.completed_at is None
        assert execution is not None
        assert execution.task == ModelTask.TUTOR.value
        assert execution.operation_type == "studio_interaction_tutor_turn"
        assert execution.success is False
        assert execution.failure_code == "RuntimeError"
        assert execution.source_message_id is None
        assert session.scalar(select(func.count()).select_from(LearningMessage)) == 0
        assert session.scalar(select(func.count()).select_from(CandidateEvent)) == 0
        assert session.scalar(select(func.count()).select_from(StudioTutorObservation)) == 0


def test_canvas_interaction_rejects_a_tutor_v9_result_missing_workspace_intent(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """A missing v9 key is invalid; it is not the explicit nullable WorkspaceIntent value."""

    from services.studio.interactions import StudioInteractionTutorOutputError

    student_id, session_id, runtime_id, _scene_id, interaction_id, engine = _triggering_interaction(
        postgres_session_factory
    )
    with pytest.raises(StudioInteractionTutorOutputError, match="workspace_intent"):
        _studio_tutor_service(engine=engine, provider=_MissingWorkspaceIntentProvider()).execute(
            student_id=student_id,
            learning_session_id=session_id,
            runtime_id=runtime_id,
            interaction_id=interaction_id,
        )

    with postgres_session_factory.begin() as session:
        interaction = session.get(StudioStudentInteraction, interaction_id)
        execution = session.scalar(select(AIExecution).where(AIExecution.operation_id == interaction_id))
        assert interaction is not None and interaction.status == "RUNNING"
        assert execution is not None and execution.success is True
        assert session.scalar(select(func.count()).select_from(LearningMessage)) == 0


def test_paused_canvas_provider_does_not_hold_the_studio_runtime_lock(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """A record-only operation commits while an admitted Canvas provider call is paused."""

    student_id, session_id, runtime_id, scene_id, interaction_id, engine = _triggering_interaction(
        postgres_session_factory
    )
    provider = _PausedStudioTutorProvider()
    service = _studio_tutor_service(engine=engine, provider=provider)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            service.execute,
            student_id=student_id,
            learning_session_id=session_id,
            runtime_id=runtime_id,
            interaction_id=interaction_id,
        )
        assert provider.started.wait(timeout=5)
        with postgres_session_factory.begin() as session:
            student = session.get(Student, student_id)
            learning_session = session.get(LearningSession, session_id)
            scene = session.get(StudioScene, scene_id)
            assert student is not None and learning_session is not None and scene is not None
            record_only = StudioStateService(session).append_event(
                _append_command(
                    runtime_id,
                    student,
                    learning_session,
                    event_kind="fixture.record",
                    action_key="fixture.record",
                    scene_id=scene_id,
                    base_scene_version=scene.scene_version,
                    actor=StudioActor.STUDENT,
                    payload={"value": 7},
                )
            )
            assert record_only.interaction is None
        provider.release.set()
        future.result(timeout=5)

    with postgres_session_factory.begin() as session:
        interaction = session.get(StudioStudentInteraction, interaction_id)
        assert interaction is not None and interaction.status == "RUNNING"
        assert session.scalar(select(func.count()).select_from(StudioStudentInteraction)) == 1


def test_competing_canvas_execution_requests_admit_one_provider_call(
    postgres_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two synchronized database transactions race the real claim; one wins and one is rejected."""

    from services.studio.interactions import StudioInteractionStateError, StudioInteractionTutorService

    student_id, session_id, runtime_id, _scene_id, interaction_id, engine = _triggering_interaction(
        postgres_session_factory
    )
    provider = _RecordingStudioTutorProvider()
    barrier = Barrier(2)
    original_claim_and_resolve = StudioInteractionTutorService._claim_and_resolve

    def synchronized_claim_and_resolve(self: object, **kwargs: object):
        barrier.wait(timeout=5)
        return original_claim_and_resolve(self, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(StudioInteractionTutorService, "_claim_and_resolve", synchronized_claim_and_resolve)

    def execute_once() -> object:
        return _studio_tutor_service(engine=engine, provider=provider).execute(
            student_id=student_id,
            learning_session_id=session_id,
            runtime_id=runtime_id,
            interaction_id=interaction_id,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(execute_once)
        second = executor.submit(execute_once)
        outcomes = [future.exception(timeout=5) for future in (first, second)]

    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(isinstance(outcome, StudioInteractionStateError) for outcome in outcomes) == 1
    assert len(provider.payloads) == 1
    with postgres_session_factory.begin() as session:
        assert session.scalar(select(func.count()).select_from(AIExecution)) == 1


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
