"""Production Science process-sequence contract and Runtime-03 regressions."""

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
from services.platform.db.models import (
    CandidateEvent,
    LearningEvidence,
    LearningMessage,
    LearningSegment,
    LearningSession,
    PersonalFact,
    StudioRuntime,
    StudioScene,
    StudioStudentInteraction,
    Student,
    User,
)
from services.platform.db.session import get_session
from services.studio.contracts import AppendStudioEventCommand, CreateSceneCommand, StudioActor
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.router import WorkspaceAuthorityContext, WorkspaceDecisionStatus, WorkspaceExecutionMode, route_workspace_intent
from services.studio.service import InvalidStudioLineage, StaleSceneVersion, StudioStateError, StudioStateService
from services.studio.subjects import PRODUCTION_CURRENT_PROFILE_VERSIONS, production_subject_registry
from services.studio.workspace_intent import WorkspaceIntent
from services.platform.safety import SafetyPolicyService
from services.retrieval.service import RetrievalService
from services.tutor.context import TutorContextBuilder
from services.tutor.runtime import TutorRuntime


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    database_url = os.getenv("DATABASE_URL")
    if database_url is None:
        pytest.skip("PostgreSQL DATABASE_URL is required for process-sequence activity contracts")
    engine = create_engine(normalize_database_url(database_url))
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
    learning_session = LearningSession(student_id=student.id, subject="SCIENCE", status="OPEN")
    session.add(learning_session)
    session.flush()
    return learning_session


def _tutor_source(session: Session, learning_session: LearningSession) -> tuple[LearningSegment, LearningMessage]:
    segment = LearningSegment(session_id=learning_session.id, sequence=1)
    session.add(segment)
    session.flush()
    message = LearningMessage(
        session_id=learning_session.id,
        segment_id=segment.id,
        role="tutor",
        content="Let us put the filtration steps in order.",
    )
    session.add(message)
    session.flush()
    return segment, message


def _science_intent() -> WorkspaceIntent:
    return WorkspaceIntent.model_validate(
        {
            "version": "workspace-intent-v1",
            "action": "OPEN_ACTIVITY",
            "subject_key": "SCIENCE",
            "concept_keys": ["filtration-sequence"],
            "learning_goal": "Put the filtration steps in a sensible scientific order.",
            "activity_hint": "process_sequence_workspace",
            "representation_need": "INTERACTIVE",
            "expected_student_response_mode": "WORKSPACE",
            "presentation_sequence": "PARALLEL",
            "source_references": [],
            "safe_text_fallback": "Let's put the filtration steps in order together.",
        }
    )


def _science_workspace_audit() -> dict[str, object]:
    decision = route_workspace_intent(
        _science_intent(),
        WorkspaceAuthorityContext(
            registry=production_subject_registry(),
            current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS,
        ),
    )
    return {
        "intent_status": "VALID",
        "intent": _science_intent().model_dump(mode="json"),
        "decision": decision.as_audit_payload(),
    }


def _science_scene_command(
    student: Student,
    learning_session: LearningSession,
    *,
    source_segment_id: UUID | None = None,
    source_message_id: UUID | None = None,
) -> CreateSceneCommand:
    from services.studio.subjects.process_sequence import (  # noqa: PLC0415 - RED contract
        ACTIVITY_KEY,
        ACTIVITY_VERSION,
        ACCESSIBILITY_PAYLOAD,
        RENDERER_KEY,
        RENDERER_VERSION,
        SCIENCE_PROFILE_VERSION,
        SCENE_PAYLOAD_SCHEMA_VERSION,
        process_sequence_scene_seed,
    )

    return CreateSceneCommand(
        student_id=student.id,
        learning_session_id=learning_session.id,
        subject_key="SCIENCE",
        subject_profile_version=SCIENCE_PROFILE_VERSION,
        concept_keys=("filtration-sequence",),
        activity_key=ACTIVITY_KEY,
        artifact_type="interactive-activity",
        renderer_key=RENDERER_KEY,
        renderer_version=RENDERER_VERSION,
        activity_contract_version=ACTIVITY_VERSION,
        payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
        seed_payload=process_sequence_scene_seed(),
        accessibility_payload=ACCESSIBILITY_PAYLOAD,
        locale="en",
        direction="auto",
        source_segment_id=source_segment_id,
        source_message_id=source_message_id,
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


def _reorder_command(
    *,
    runtime_id: UUID,
    student: Student,
    learning_session: LearningSession,
    scene: StudioScene,
    stage_id: str,
    from_index: int,
    to_index: int,
    idempotency_key: str,
    base_scene_version: int | None = None,
) -> AppendStudioEventCommand:
    from services.studio.subjects.process_sequence import REORDER_PAYLOAD_SCHEMA_VERSION, REORDER_STAGE_ACTION_KEY

    return AppendStudioEventCommand(
        runtime_id=runtime_id,
        student_id=student.id,
        learning_session_id=learning_session.id,
        event_kind=None,
        event_schema_version=None,
        actor=StudioActor.STUDENT,
        action_key=REORDER_STAGE_ACTION_KEY,
        payload_schema_version=REORDER_PAYLOAD_SCHEMA_VERSION,
        payload={"stage_id": stage_id, "from_index": from_index, "to_index": to_index},
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
    stage_ids: list[str],
    idempotency_key: str,
) -> AppendStudioEventCommand:
    from services.studio.subjects.process_sequence import SUBMIT_CONFIGURATION_ACTION_KEY, SUBMIT_PAYLOAD_SCHEMA_VERSION

    return AppendStudioEventCommand(
        runtime_id=runtime_id,
        student_id=student.id,
        learning_session_id=learning_session.id,
        event_kind=None,
        event_schema_version=None,
        actor=StudioActor.STUDENT,
        action_key=SUBMIT_CONFIGURATION_ACTION_KEY,
        payload_schema_version=SUBMIT_PAYLOAD_SCHEMA_VERSION,
        payload={"stage_ids": stage_ids},
        scene_id=scene.id,
        base_scene_version=scene.scene_version,
        idempotency_key=idempotency_key,
    )


def test_science_v2_registers_the_exact_process_sequence_contract_without_mutating_v1() -> None:
    """The new production capability is exact, routable, and leaves Science v1 replayable."""

    from services.studio.subjects.process_sequence import (  # noqa: PLC0415 - RED contract
        ACTIVITY_KEY,
        ACTIVITY_VERSION,
        RENDERER_KEY,
        RENDERER_VERSION,
        SCIENCE_PROFILE_VERSION,
        SUBMIT_CONFIGURATION_ACTION_KEY,
        REORDER_STAGE_ACTION_KEY,
    )

    registry = production_subject_registry()
    assert PRODUCTION_CURRENT_PROFILE_VERSIONS["SCIENCE"] == SCIENCE_PROFILE_VERSION
    assert registry.activities_for_profile("SCIENCE", "subject-profile-v1") == ()
    activity = registry.resolve_activity("SCIENCE", SCIENCE_PROFILE_VERSION, ACTIVITY_KEY, ACTIVITY_VERSION)
    renderer = registry.resolve_renderer("SCIENCE", SCIENCE_PROFILE_VERSION, RENDERER_KEY, RENDERER_VERSION)
    assert {action.action_key for action in activity.actions} == {
        REORDER_STAGE_ACTION_KEY,
        SUBMIT_CONFIGURATION_ACTION_KEY,
    }
    assert renderer.interactive is True

    decision = route_workspace_intent(
        _science_intent(),
        WorkspaceAuthorityContext(registry=registry, current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS),
    )
    assert decision.status is WorkspaceDecisionStatus.ROUTED
    assert decision.mode is WorkspaceExecutionMode.KNOWN_INTERACTIVE
    assert decision.selected_subject_key == "SCIENCE"
    assert decision.selected_activity_key == ACTIVITY_KEY
    assert decision.selected_activity_version == ACTIVITY_VERSION


def test_science_activation_requires_exact_audit_and_reuses_the_exact_accepted_scene(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Activation never chooses a Scene by Tutor source alone and exact retries are idempotent."""

    from services.studio.process_sequence_activation import activate_process_sequence_from_workspace_decision  # noqa: PLC0415 - RED contract

    with postgres_session_factory.begin() as session:
        student = _student(session, "science-activation")
        learning_session = _learning_session(session, student)
        segment, source_message = _tutor_source(session, learning_session)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        accepted = service.accept_scene(
            _science_scene_command(
                student,
                learning_session,
                source_segment_id=segment.id,
                source_message_id=source_message.id,
            )
        )

        rejected = activate_process_sequence_from_workspace_decision(
            session,
            learning_session=learning_session,
            source_tutor_message=source_message,
            source_segment_id=segment.id,
            workspace_audit={"intent_status": "INVALID"},
        )
        assert rejected is None
        assert accepted.status == "ACCEPTED"

        activated = activate_process_sequence_from_workspace_decision(
            session,
            learning_session=learning_session,
            source_tutor_message=source_message,
            source_segment_id=segment.id,
            workspace_audit=_science_workspace_audit(),
        )
        assert activated is not None and activated.id == accepted.id and activated.status == "ACTIVE"

        repeated = activate_process_sequence_from_workspace_decision(
            session,
            learning_session=learning_session,
            source_tutor_message=source_message,
            source_segment_id=segment.id,
            workspace_audit=_science_workspace_audit(),
        )
        assert repeated is not None and repeated.id == accepted.id
        assert session.scalar(select(func.count()).select_from(StudioScene)) == 1
        assert session.get(StudioRuntime, runtime.id) is not None


def test_process_sequence_reorder_and_submit_are_durable_rebuildable_and_bounded(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Reorder is record-only; a structurally valid wrong order persists as bounded feedback."""

    from services.studio.subjects.process_sequence import (
        ACTIVITY_KEY,
        ALLOW_FILTER_STAGE_ID,
        COLLECT_WATER_STAGE_ID,
        POUR_MIXTURE_STAGE_ID,
        PREPARE_FILTER_STAGE_ID,
        process_sequence_scene_seed,
    )

    with postgres_session_factory.begin() as session:
        student = _student(session, "science-state")
        learning_session = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        scene = service.accept_scene(_science_scene_command(student, learning_session))
        _activate(service, runtime_id=runtime.id, student=student, learning_session=learning_session, scene=scene)
        initial_stage_ids = list(process_sequence_scene_seed()["stage_ids"])
        assert scene.seed_payload == process_sequence_scene_seed()
        assert initial_stage_ids == [
            ALLOW_FILTER_STAGE_ID,
            PREPARE_FILTER_STAGE_ID,
            COLLECT_WATER_STAGE_ID,
            POUR_MIXTURE_STAGE_ID,
        ]

        first_reorder = _reorder_command(
            runtime_id=runtime.id,
            student=student,
            learning_session=learning_session,
            scene=scene,
            stage_id=PREPARE_FILTER_STAGE_ID,
            from_index=1,
            to_index=0,
            idempotency_key="process-sequence-reorder-prepare",
        )
        first = service.append_event(first_reorder)
        assert first.event.resulting_scene_version == scene.scene_version == 3
        assert service.runtime_state(runtime_id=runtime.id, student_id=student.id)["snapshot"]["current_scene_version"] == 3
        assert first.interaction is None
        assert first.event.payload == {
            "action": {"stage_id": PREPARE_FILTER_STAGE_ID, "from_index": 1, "to_index": 0}
        }
        replay = service.append_event(first_reorder)
        assert replay.replayed is True and replay.event.id == first.event.id

        second = service.append_event(
            _reorder_command(
                runtime_id=runtime.id,
                student=student,
                learning_session=learning_session,
                scene=scene,
                stage_id=POUR_MIXTURE_STAGE_ID,
                from_index=3,
                to_index=1,
                idempotency_key="process-sequence-reorder-pour",
            )
        )
        assert second.interaction is None
        projection = service.runtime_state(runtime_id=runtime.id, student_id=student.id)["snapshot"]
        assert projection["current_scene_version"] == scene.scene_version == second.event.resulting_scene_version == 4
        assert projection["state_payload"][ACTIVITY_KEY]["stage_ids"] == [
            PREPARE_FILTER_STAGE_ID,
            POUR_MIXTURE_STAGE_ID,
            ALLOW_FILTER_STAGE_ID,
            COLLECT_WATER_STAGE_ID,
        ]
        assert service.rebuild_snapshot(runtime_id=runtime.id, student_id=student.id) == projection

        valid_stage_ids = list(projection["state_payload"][ACTIVITY_KEY]["stage_ids"])
        submission_command = _submit_command(
            runtime_id=runtime.id,
            student=student,
            learning_session=learning_session,
            scene=scene,
            stage_ids=valid_stage_ids,
            idempotency_key="process-sequence-submit-valid",
        )
        submission = service.append_event(submission_command)
        assert submission.interaction is not None
        assert submission.event.payload["validation"] == {
            "status": "VALID",
            "feedback_code": "FILTRATION_SEQUENCE_COMPLETE",
            "next_action_keys": [],
        }
        replayed_submission = service.append_event(submission_command)
        assert replayed_submission.replayed is True
        assert replayed_submission.event.id == submission.event.id
        assert replayed_submission.interaction is not None
        assert replayed_submission.interaction.id == submission.interaction.id

        changed_after_submit = service.append_event(
            _reorder_command(
                runtime_id=runtime.id,
                student=student,
                learning_session=learning_session,
                scene=scene,
                stage_id=ALLOW_FILTER_STAGE_ID,
                from_index=2,
                to_index=1,
                idempotency_key="process-sequence-reorder-after-submit",
            )
        )
        assert changed_after_submit.interaction is None
        current_stage_ids = service.runtime_state(runtime_id=runtime.id, student_id=student.id)["snapshot"]["state_payload"][ACTIVITY_KEY]["stage_ids"]
        invalid = service.append_event(
            _submit_command(
                runtime_id=runtime.id,
                student=student,
                learning_session=learning_session,
                scene=scene,
                stage_ids=list(current_stage_ids),
                idempotency_key="process-sequence-submit-invalid",
            )
        )
        assert invalid.interaction is not None
        assert invalid.event.payload["validation"] == {
            "status": "INVALID",
            "feedback_code": "FILTRATION_SEQUENCE_NEEDS_REORDERING",
            "next_action_keys": ["REORDER_STAGE", "SUBMIT_CONFIGURATION"],
        }

        before_rejection = service.runtime_state(runtime_id=runtime.id, student_id=student.id)
        with pytest.raises(StudioStateError):
            service.append_event(
                _reorder_command(
                    runtime_id=runtime.id,
                    student=student,
                    learning_session=learning_session,
                    scene=scene,
                    stage_id="unknown-stage",
                    from_index=0,
                    to_index=1,
                    idempotency_key="process-sequence-unknown-stage",
                )
            )
        from services.studio.subjects.process_sequence import REORDER_PAYLOAD_SCHEMA_VERSION, REORDER_STAGE_ACTION_KEY

        with pytest.raises(StudioStateError):
            service.append_event(
                AppendStudioEventCommand(
                    runtime_id=runtime.id,
                    student_id=student.id,
                    learning_session_id=learning_session.id,
                    event_kind=None,
                    event_schema_version=None,
                    actor=StudioActor.STUDENT,
                    action_key=REORDER_STAGE_ACTION_KEY,
                    payload_schema_version=REORDER_PAYLOAD_SCHEMA_VERSION,
                    payload={"stage_id": PREPARE_FILTER_STAGE_ID, "from_index": "one", "to_index": 0},
                    scene_id=scene.id,
                    base_scene_version=scene.scene_version,
                    idempotency_key="process-sequence-malformed-reorder",
                )
            )
        with pytest.raises(StudioStateError):
            service.append_event(
                _submit_command(
                    runtime_id=runtime.id,
                    student=student,
                    learning_session=learning_session,
                    scene=scene,
                    stage_ids=[PREPARE_FILTER_STAGE_ID] * 4,
                    idempotency_key="process-sequence-duplicate-stage",
                )
            )
        with pytest.raises(StudioStateError):
            service.append_event(
                _submit_command(
                    runtime_id=runtime.id,
                    student=student,
                    learning_session=learning_session,
                    scene=scene,
                    stage_ids=list(current_stage_ids)[:-1],
                    idempotency_key="process-sequence-missing-stage",
                )
            )
        with pytest.raises(StudioStateError):
            service.append_event(
                _submit_command(
                    runtime_id=runtime.id,
                    student=student,
                    learning_session=learning_session,
                    scene=scene,
                    stage_ids=[*current_stage_ids, "extra-stage"],
                    idempotency_key="process-sequence-extra-stage",
                )
            )
        assert service.runtime_state(runtime_id=runtime.id, student_id=student.id) == before_rejection

        with pytest.raises(StaleSceneVersion):
            service.append_event(
                _reorder_command(
                    runtime_id=runtime.id,
                    student=student,
                    learning_session=learning_session,
                    scene=scene,
                    stage_id=ALLOW_FILTER_STAGE_ID,
                    from_index=2,
                    to_index=1,
                    base_scene_version=scene.scene_version - 1,
                    idempotency_key="process-sequence-stale",
                )
            )
        other = _student(session, "science-other")
        with pytest.raises(InvalidStudioLineage):
            service.append_event(
                _submit_command(
                    runtime_id=runtime.id,
                    student=other,
                    learning_session=learning_session,
                    scene=scene,
                    stage_ids=list(current_stage_ids),
                    idempotency_key="process-sequence-other-student",
                )
            )
        assert session.scalar(select(func.count()).select_from(CandidateEvent)) == 0
        assert session.scalar(select(func.count()).select_from(LearningEvidence)) == 0
        assert session.scalar(select(func.count()).select_from(PersonalFact)) == 0
        assert session.scalar(select(func.count()).select_from(StudioStudentInteraction)) == 2


def test_normal_tutor_turn_activates_only_the_exact_persisted_science_decision(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Runtime-03 invokes one compact adapter seam after the primary Tutor call persists."""

    from services.platform.db.models import ModelTask

    class Provider:
        calls = 0

        def stream(self, route: ModelRoute, payload: dict[str, object]):
            del route, payload
            self.calls += 1
            yield StreamDelta("Let us order the filtration steps together.")
            yield StreamComplete(
                ModelResult(
                    output={
                        "text": "Let us order the filtration steps together.",
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
                        "workspace_intent": _science_intent().model_dump(mode="json"),
                    }
                )
            )

    with postgres_session_factory.begin() as session:
        student = _student(session, "science-normal-tutor")
        learning_session = _learning_session(session, student)
        student_id, learning_session_id = student.id, learning_session.id

    provider = Provider()
    with postgres_session_factory.begin() as session:
        learning_session = session.get(LearningSession, learning_session_id)
        assert learning_session is not None
        runtime = TutorRuntime(
            session,
            context_builder=TutorContextBuilder(session, retrieval_service=RetrievalService(session)),
            safety_policy=SafetyPolicyService(session),
            gateway=ModelGateway(
                session,
                routes={ModelTask.TUTOR: ModelRoute("fixture", "science-process-sequence-tutor")},
                providers={"fixture": provider},
            ),
        )
        list(runtime.stream_turn(learning_session=learning_session, question="How do we filter sand from water?"))

    with postgres_session_factory.begin() as session:
        scene = session.scalar(select(StudioScene).where(StudioScene.learning_session_id == learning_session_id))
        tutor_message = session.scalar(
            select(LearningMessage).where(
                LearningMessage.session_id == learning_session_id,
                LearningMessage.role == "tutor",
            )
        )
        assert provider.calls == 1
        assert scene is not None and tutor_message is not None
        assert scene.status == "ACTIVE"
        assert scene.student_id == student_id
        assert scene.source_message_id == tutor_message.id
        assert scene.source_segment_id == tutor_message.segment_id
        assert scene.activity_key == "process_sequence_workspace"
        assert session.scalar(select(func.count()).select_from(StudioStudentInteraction)) == 0


def _client(factory: sessionmaker[Session], *, subject: str) -> TestClient:
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


def test_process_sequence_submission_uses_original_source_after_later_record_only_reorder(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tutor continuation receives source submission truth and a separate current snapshot."""

    from apps.api.routes import student as student_routes
    from services.platform.db.models import ModelTask, StudioCanvasSpecialistRun
    from services.studio.subjects.process_sequence import (
        ALLOW_FILTER_STAGE_ID,
        COLLECT_WATER_STAGE_ID,
        POUR_MIXTURE_STAGE_ID,
        PREPARE_FILTER_STAGE_ID,
        REORDER_STAGE_ACTION_KEY,
        SUBMIT_CONFIGURATION_ACTION_KEY,
    )

    valid_stage_ids = [
        PREPARE_FILTER_STAGE_ID,
        POUR_MIXTURE_STAGE_ID,
        ALLOW_FILTER_STAGE_ID,
        COLLECT_WATER_STAGE_ID,
    ]
    changed_stage_ids = [
        PREPARE_FILTER_STAGE_ID,
        ALLOW_FILTER_STAGE_ID,
        POUR_MIXTURE_STAGE_ID,
        COLLECT_WATER_STAGE_ID,
    ]

    class Provider:
        calls = 0

        def stream(self, route: ModelRoute, payload: dict[str, object]):
            del route
            self.calls += 1
            source_event = payload["studio_interaction_context"]["source"]["event"]
            live_subject = payload["studio_interaction_context"]["source"]["live_subject"]
            source_state = source_event["action_payload"]
            source_validation = source_event["validation"]
            current_state = payload["studio_interaction_context"]["workspace"]["state"]["process_sequence_workspace"]
            selected_state = payload["studio_workspace_context"]["snapshot"]["state"]["process_sequence_workspace"]
            assert source_state == {"stage_ids": valid_stage_ids}
            assert live_subject == {
                "broad_subject": "SCIENCE",
                "origin": "CANVAS_SCENE",
                "source_scene_id": source_event["scene_id"],
            }
            assert source_validation == {
                "status": "VALID",
                "feedback_code": "FILTRATION_SEQUENCE_COMPLETE",
                "next_action_keys": [],
            }
            assert current_state["stage_ids"] == changed_stage_ids
            assert current_state == selected_state
            yield StreamDelta("You put the filtration steps in a useful order.")
            yield StreamComplete(
                ModelResult(
                    output={"text": "You put the filtration steps in a useful order.", "workspace_intent": None}
                )
            )

    with postgres_session_factory.begin() as session:
        student = _student(session, "science-api")
        learning_session = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        scene = service.accept_scene(_science_scene_command(student, learning_session))
        _activate(service, runtime_id=runtime.id, student=student, learning_session=learning_session, scene=scene)
        runtime_id, scene_id, scene_version, student_id, learning_session_id = (
            runtime.id,
            scene.id,
            scene.scene_version,
            student.id,
            learning_session.id,
        )

    provider = Provider()
    monkeypatch.setattr(
        student_routes,
        "create_studio_interaction_tutor_gateway",
        lambda gateway_session: ModelGateway(
            gateway_session,
            routes={ModelTask.TUTOR: ModelRoute("fixture", "science-process-sequence-continuation")},
            providers={"fixture": provider},
        ),
    )
    client = _client(postgres_session_factory, subject="science-api")
    try:
        prepare = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id),
                "base_scene_version": scene_version,
                "action_key": REORDER_STAGE_ACTION_KEY,
                "payload": {"stage_id": PREPARE_FILTER_STAGE_ID, "from_index": 1, "to_index": 0},
                "idempotency_key": "api-process-sequence-prepare",
            },
        )
        assert prepare.status_code == 200 and prepare.json()["student_interaction_id"] is None

        with postgres_session_factory.begin() as session:
            current_scene = session.get(StudioScene, scene_id)
            assert current_scene is not None
            current_scene_version = current_scene.scene_version

        pour = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id),
                "base_scene_version": current_scene_version,
                "action_key": REORDER_STAGE_ACTION_KEY,
                "payload": {"stage_id": POUR_MIXTURE_STAGE_ID, "from_index": 3, "to_index": 1},
                "idempotency_key": "api-process-sequence-pour",
            },
        )
        assert pour.status_code == 200 and pour.json()["student_interaction_id"] is None

        with postgres_session_factory.begin() as session:
            current_scene = session.get(StudioScene, scene_id)
            assert current_scene is not None
            current_scene_version = current_scene.scene_version

        submit = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id),
                "base_scene_version": current_scene_version,
                "action_key": SUBMIT_CONFIGURATION_ACTION_KEY,
                "payload": {"stage_ids": valid_stage_ids},
                "idempotency_key": "api-process-sequence-submit",
            },
        )
        assert submit.status_code == 200
        interaction_id = submit.json()["student_interaction_id"]
        assert interaction_id and submit.json()["student_interaction_status"] == "PENDING"

        with postgres_session_factory.begin() as session:
            current_scene = session.get(StudioScene, scene_id)
            interaction = session.get(StudioStudentInteraction, UUID(interaction_id))
            assert current_scene is not None and interaction is not None
            assert interaction.status == "PENDING"
            submitted_scene_version = current_scene.scene_version

        later_reorder = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id),
                "base_scene_version": submitted_scene_version,
                "action_key": REORDER_STAGE_ACTION_KEY,
                "payload": {"stage_id": ALLOW_FILTER_STAGE_ID, "from_index": 2, "to_index": 1},
                "idempotency_key": "api-process-sequence-reorder-after-submit",
            },
        )
        assert later_reorder.status_code == 200 and later_reorder.json()["student_interaction_id"] is None

        stream = client.post(f"/api/v1/student/studio/{runtime_id}/interactions/{interaction_id}/turn/stream")
        assert stream.status_code == 200
        assert provider.calls == 1
        with postgres_session_factory.begin() as session:
            messages = list(
                session.scalars(select(LearningMessage).where(LearningMessage.session_id == learning_session_id))
            )
            assert [(message.role, message.content) for message in messages] == [
                ("tutor", "You put the filtration steps in a useful order.")
            ]
            interaction = session.get(StudioStudentInteraction, UUID(interaction_id))
            assert interaction is not None and interaction.status == "COMPLETED"
            assert interaction.tutor_message_id == messages[0].id
            assert session.scalar(select(func.count()).select_from(CandidateEvent)) == 0
            assert session.scalar(select(func.count()).select_from(LearningEvidence)) == 0
            assert session.scalar(select(func.count()).select_from(PersonalFact)) == 0
            assert session.scalar(select(func.count()).select_from(StudioCanvasSpecialistRun)) == 0
            assert session.scalar(select(func.count()).select_from(StudioStudentInteraction)) == 1
            assert session.scalar(select(func.count()).select_from(StudioRuntime)) == 1
            runtime = session.get(StudioRuntime, runtime_id)
            assert runtime is not None and runtime.student_id == student_id
    finally:
        _clear_overrides()
