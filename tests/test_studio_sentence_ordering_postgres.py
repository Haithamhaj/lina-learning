"""Production English sentence-ordering contract and Runtime-03 regressions."""

from __future__ import annotations

import os
import re
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


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    database_url = os.getenv("DATABASE_URL")
    if database_url is None:
        pytest.skip("PostgreSQL DATABASE_URL is required for sentence-ordering activity contracts")
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
    learning_session = LearningSession(student_id=student.id, subject="ENGLISH", status="OPEN")
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
        content="Let us put these English words in order.",
    )
    session.add(message)
    session.flush()
    return segment, message


def _english_intent() -> WorkspaceIntent:
    return WorkspaceIntent.model_validate(
        {
            "version": "workspace-intent-v1",
            "action": "OPEN_ACTIVITY",
            "subject_key": "ENGLISH",
            "concept_keys": ["sentence-order"],
            "learning_goal": "Put the declared English words into one sentence order.",
            "activity_hint": "sentence_ordering_workspace",
            "representation_need": "INTERACTIVE",
            "expected_student_response_mode": "WORKSPACE",
            "presentation_sequence": "PARALLEL",
            "source_references": [],
            "safe_text_fallback": "Let us put the words in order together.",
        }
    )


def _english_workspace_audit() -> dict[str, object]:
    decision = route_workspace_intent(
        _english_intent(),
        WorkspaceAuthorityContext(
            registry=production_subject_registry(),
            current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS,
        ),
    )
    return {
        "intent_status": "VALID",
        "intent": _english_intent().model_dump(mode="json"),
        "decision": decision.as_audit_payload(),
    }


def _english_scene_command(
    student: Student,
    learning_session: LearningSession,
    *,
    source_segment_id: UUID | None = None,
    source_message_id: UUID | None = None,
) -> CreateSceneCommand:
    from services.studio.subjects.sentence_ordering import (  # noqa: PLC0415 - RED contract
        ACTIVITY_KEY,
        ACTIVITY_VERSION,
        ACCESSIBILITY_PAYLOAD,
        ENGLISH_PROFILE_VERSION,
        RENDERER_KEY,
        RENDERER_VERSION,
        SCENE_PAYLOAD_SCHEMA_VERSION,
        sentence_ordering_scene_seed,
    )

    return CreateSceneCommand(
        student_id=student.id,
        learning_session_id=learning_session.id,
        subject_key="ENGLISH",
        subject_profile_version=ENGLISH_PROFILE_VERSION,
        concept_keys=("sentence-order",),
        activity_key=ACTIVITY_KEY,
        artifact_type="interactive-activity",
        renderer_key=RENDERER_KEY,
        renderer_version=RENDERER_VERSION,
        activity_contract_version=ACTIVITY_VERSION,
        payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
        seed_payload=sentence_ordering_scene_seed(),
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
    token_id: str,
    from_index: int,
    to_index: int,
    idempotency_key: str,
    base_scene_version: int | None = None,
) -> AppendStudioEventCommand:
    from services.studio.subjects.sentence_ordering import REORDER_PAYLOAD_SCHEMA_VERSION, REORDER_TOKEN_ACTION_KEY  # noqa: PLC0415 - RED contract

    return AppendStudioEventCommand(
        runtime_id=runtime_id,
        student_id=student.id,
        learning_session_id=learning_session.id,
        event_kind=None,
        event_schema_version=None,
        actor=StudioActor.STUDENT,
        action_key=REORDER_TOKEN_ACTION_KEY,
        payload_schema_version=REORDER_PAYLOAD_SCHEMA_VERSION,
        payload={"token_id": token_id, "from_index": from_index, "to_index": to_index},
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
    token_ids: list[str],
    idempotency_key: str,
) -> AppendStudioEventCommand:
    from services.studio.subjects.sentence_ordering import SUBMIT_CONFIGURATION_ACTION_KEY, SUBMIT_PAYLOAD_SCHEMA_VERSION  # noqa: PLC0415 - RED contract

    return AppendStudioEventCommand(
        runtime_id=runtime_id,
        student_id=student.id,
        learning_session_id=learning_session.id,
        event_kind=None,
        event_schema_version=None,
        actor=StudioActor.STUDENT,
        action_key=SUBMIT_CONFIGURATION_ACTION_KEY,
        payload_schema_version=SUBMIT_PAYLOAD_SCHEMA_VERSION,
        payload={"token_ids": token_ids},
        scene_id=scene.id,
        base_scene_version=scene.scene_version,
        idempotency_key=idempotency_key,
    )


def test_english_v2_registers_exact_sentence_ordering_contract_and_preserves_v1() -> None:
    """Changing the current English profile or a token ID must break exact resolution."""

    from services.studio.subjects.sentence_ordering import (  # noqa: PLC0415 - RED contract
        ACTIVITY_KEY,
        ACTIVITY_VERSION,
        ENGLISH_PROFILE_VERSION,
        RENDERER_KEY,
        RENDERER_VERSION,
        REORDER_TOKEN_ACTION_KEY,
        SUBMIT_CONFIGURATION_ACTION_KEY,
        validate_token_catalog,
    )

    registry = production_subject_registry()
    assert PRODUCTION_CURRENT_PROFILE_VERSIONS["ENGLISH"] == ENGLISH_PROFILE_VERSION
    assert registry.activities_for_profile("ENGLISH", "subject-profile-v1") == ()
    activity = registry.resolve_activity("ENGLISH", ENGLISH_PROFILE_VERSION, ACTIVITY_KEY, ACTIVITY_VERSION)
    renderer = registry.resolve_renderer("ENGLISH", ENGLISH_PROFILE_VERSION, RENDERER_KEY, RENDERER_VERSION)
    assert {action.action_key for action in activity.actions} == {REORDER_TOKEN_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY}
    assert renderer.interactive is True

    duplicate_visible_labels = [
        {"id": "article-subject", "text": "the"},
        {"id": "article-object", "text": "the"},
    ]
    validate_token_catalog(duplicate_visible_labels, label="Duplicate-label contract fixture")
    assert duplicate_visible_labels[0]["id"] != duplicate_visible_labels[1]["id"]
    assert duplicate_visible_labels[0]["text"] == duplicate_visible_labels[1]["text"] == "the"

    decision = route_workspace_intent(
        _english_intent(),
        WorkspaceAuthorityContext(registry=registry, current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS),
    )
    assert decision.status is WorkspaceDecisionStatus.ROUTED
    assert decision.mode is WorkspaceExecutionMode.KNOWN_INTERACTIVE
    assert decision.selected_subject_key == "ENGLISH"
    assert decision.selected_activity_key == ACTIVITY_KEY
    assert decision.selected_activity_version == ACTIVITY_VERSION


def test_sentence_ordering_seed_uses_opaque_identity_without_browser_answer_metadata() -> None:
    """The browser-safe seed may identify tokens, but cannot reconstruct the authored answer."""

    from services.studio.subjects.sentence_ordering import (  # noqa: PLC0415 - RED contract
        BIRDS_TOKEN_ID,
        CLOUDS_TOKEN_ID,
        FLY_TOKEN_ID,
        OVER_TOKEN_ID,
        sentence_ordering_scene_seed,
        validate_token_catalog,
    )

    canonical_order = [BIRDS_TOKEN_ID, FLY_TOKEN_ID, OVER_TOKEN_ID, CLOUDS_TOKEN_ID]
    seed = sentence_ordering_scene_seed()
    catalog = seed["tokens"]
    assert isinstance(catalog, list)
    catalog_ids = [token["id"] for token in catalog]
    assert catalog_ids != canonical_order
    assert sorted(catalog_ids) != canonical_order
    assert seed["token_ids"] != canonical_order
    assert all(re.fullmatch(r"tok-[0-9a-f]{4}", token_id) for token_id in canonical_order)
    assert all(label.lower() not in token_id for token_id, label in ((token["id"], token["text"]) for token in catalog))
    assert not any("answer" in key or "accepted" in key or "valid" in key for key in seed)

    renamed_labels = validate_token_catalog(
        [{"id": token["id"], "text": f"renamed-{index}"} for index, token in enumerate(catalog)],
        label="Opaque identity label-change fixture",
    )
    assert [token["id"] for token in renamed_labels] == catalog_ids
    duplicate_labels = validate_token_catalog(
        [{"id": "tok-1a2b", "text": "the"}, {"id": "tok-3c4d", "text": "the"}],
        label="Opaque duplicate-label contract fixture",
    )
    assert duplicate_labels[0]["id"] != duplicate_labels[1]["id"]


def test_english_activation_requires_exact_audit_and_reuses_only_exact_scene(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Removing exact profile or renderer identity must stop activation, not select a nearby Scene."""

    from services.studio.sentence_ordering_activation import activate_sentence_ordering_from_workspace_decision  # noqa: PLC0415 - RED contract

    with postgres_session_factory.begin() as session:
        student = _student(session, "english-activation")
        learning_session = _learning_session(session, student)
        segment, source_message = _tutor_source(session, learning_session)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        accepted = service.accept_scene(
            _english_scene_command(
                student,
                learning_session,
                source_segment_id=segment.id,
                source_message_id=source_message.id,
            )
        )

        assert activate_sentence_ordering_from_workspace_decision(
            session,
            learning_session=learning_session,
            source_tutor_message=source_message,
            source_segment_id=segment.id,
            workspace_audit={"intent_status": "INVALID"},
        ) is None
        assert accepted.status == "ACCEPTED"

        activated = activate_sentence_ordering_from_workspace_decision(
            session,
            learning_session=learning_session,
            source_tutor_message=source_message,
            source_segment_id=segment.id,
            workspace_audit=_english_workspace_audit(),
        )
        assert activated is not None and activated.id == accepted.id and activated.status == "ACTIVE"
        repeated = activate_sentence_ordering_from_workspace_decision(
            session,
            learning_session=learning_session,
            source_tutor_message=source_message,
            source_segment_id=segment.id,
            workspace_audit=_english_workspace_audit(),
        )
        assert repeated is not None and repeated.id == accepted.id
        assert session.scalar(select(func.count()).select_from(StudioScene)) == 1
        assert session.get(StudioRuntime, runtime.id) is not None


def test_sentence_ordering_persists_token_identity_rebuilds_and_rejects_invalid_operations(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Wrong payload identity or stale ownership must not mutate the durable token order."""

    from services.studio.subjects.sentence_ordering import (
        ACTIVITY_KEY,
        BIRDS_TOKEN_ID,
        CLOUDS_TOKEN_ID,
        FLY_TOKEN_ID,
        OVER_TOKEN_ID,
        sentence_ordering_scene_seed,
    )

    with postgres_session_factory.begin() as session:
        student = _student(session, "english-state")
        learning_session = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        scene = service.accept_scene(_english_scene_command(student, learning_session))
        _activate(service, runtime_id=runtime.id, student=student, learning_session=learning_session, scene=scene)
        assert scene.seed_payload == sentence_ordering_scene_seed()
        assert sentence_ordering_scene_seed()["token_ids"] == [CLOUDS_TOKEN_ID, BIRDS_TOKEN_ID, OVER_TOKEN_ID, FLY_TOKEN_ID]

        first_command = _reorder_command(
            runtime_id=runtime.id,
            student=student,
            learning_session=learning_session,
            scene=scene,
            token_id=BIRDS_TOKEN_ID,
            from_index=1,
            to_index=0,
            idempotency_key="sentence-ordering-reorder-birds",
        )
        first = service.append_event(first_command)
        assert first.interaction is None
        assert first.event.payload == {"action": {"token_id": BIRDS_TOKEN_ID, "from_index": 1, "to_index": 0}}
        replay = service.append_event(first_command)
        assert replay.replayed is True and replay.event.id == first.event.id and replay.interaction is None

        second = service.append_event(
            _reorder_command(
                runtime_id=runtime.id,
                student=student,
                learning_session=learning_session,
                scene=scene,
                token_id=FLY_TOKEN_ID,
                from_index=3,
                to_index=1,
                idempotency_key="sentence-ordering-reorder-fly",
            )
        )
        assert second.interaction is None
        third = service.append_event(
            _reorder_command(
                runtime_id=runtime.id,
                student=student,
                learning_session=learning_session,
                scene=scene,
                token_id=OVER_TOKEN_ID,
                from_index=3,
                to_index=2,
                idempotency_key="sentence-ordering-reorder-over",
            )
        )
        assert third.interaction is None
        projection = service.runtime_state(runtime_id=runtime.id, student_id=student.id)["snapshot"]
        valid_token_ids = [BIRDS_TOKEN_ID, FLY_TOKEN_ID, OVER_TOKEN_ID, CLOUDS_TOKEN_ID]
        assert projection["state_payload"][ACTIVITY_KEY]["token_ids"] == valid_token_ids
        assert service.rebuild_snapshot(runtime_id=runtime.id, student_id=student.id) == projection

        valid_submission = _submit_command(
            runtime_id=runtime.id,
            student=student,
            learning_session=learning_session,
            scene=scene,
            token_ids=valid_token_ids,
            idempotency_key="sentence-ordering-submit-valid",
        )
        submitted = service.append_event(valid_submission)
        assert submitted.interaction is not None
        assert submitted.event.payload["validation"] == {
            "status": "VALID",
            "feedback_code": "SENTENCE_ORDER_COMPLETE",
            "next_action_keys": [],
        }
        replayed_submission = service.append_event(valid_submission)
        assert replayed_submission.replayed is True
        assert replayed_submission.interaction is not None
        assert replayed_submission.interaction.id == submitted.interaction.id

        changed_after_submit = service.append_event(
            _reorder_command(
                runtime_id=runtime.id,
                student=student,
                learning_session=learning_session,
                scene=scene,
                token_id=OVER_TOKEN_ID,
                from_index=2,
                to_index=1,
                idempotency_key="sentence-ordering-reorder-after-submit",
            )
        )
        assert changed_after_submit.interaction is None
        current_token_ids = service.runtime_state(runtime_id=runtime.id, student_id=student.id)["snapshot"]["state_payload"][ACTIVITY_KEY]["token_ids"]
        invalid = service.append_event(
            _submit_command(
                runtime_id=runtime.id,
                student=student,
                learning_session=learning_session,
                scene=scene,
                token_ids=list(current_token_ids),
                idempotency_key="sentence-ordering-submit-invalid",
            )
        )
        assert invalid.interaction is not None
        assert invalid.event.payload["validation"] == {
            "status": "INVALID",
            "feedback_code": "SENTENCE_ORDER_NEEDS_REORDERING",
            "next_action_keys": ["REORDER_TOKEN", "SUBMIT_CONFIGURATION"],
        }

        before_rejection = service.runtime_state(runtime_id=runtime.id, student_id=student.id)
        with pytest.raises(StudioStateError):
            service.append_event(
                _reorder_command(
                    runtime_id=runtime.id,
                    student=student,
                    learning_session=learning_session,
                    scene=scene,
                    token_id="unknown-token",
                    from_index=0,
                    to_index=1,
                    idempotency_key="sentence-ordering-unknown-token",
                )
            )
        with pytest.raises(StudioStateError):
            service.append_event(
                _submit_command(
                    runtime_id=runtime.id,
                    student=student,
                    learning_session=learning_session,
                    scene=scene,
                    token_ids=[current_token_ids[0], current_token_ids[0], *current_token_ids[2:]],
                    idempotency_key="sentence-ordering-duplicate-token",
                )
            )
        with pytest.raises(StudioStateError):
            service.append_event(
                _submit_command(
                    runtime_id=runtime.id,
                    student=student,
                    learning_session=learning_session,
                    scene=scene,
                    token_ids=list(current_token_ids)[:-1],
                    idempotency_key="sentence-ordering-missing-token",
                )
            )
        with pytest.raises(StudioStateError):
            service.append_event(
                _submit_command(
                    runtime_id=runtime.id,
                    student=student,
                    learning_session=learning_session,
                    scene=scene,
                    token_ids=[*current_token_ids, "extra-token"],
                    idempotency_key="sentence-ordering-extra-token",
                )
            )
        with pytest.raises(StudioStateError):
            service.append_event(
                _submit_command(
                    runtime_id=runtime.id,
                    student=student,
                    learning_session=learning_session,
                    scene=scene,
                    token_ids=valid_token_ids,
                    idempotency_key="sentence-ordering-snapshot-mismatch",
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
                    token_id=OVER_TOKEN_ID,
                    from_index=1,
                    to_index=2,
                    base_scene_version=scene.scene_version - 1,
                    idempotency_key="sentence-ordering-stale",
                )
            )
        other = _student(session, "english-other")
        with pytest.raises(InvalidStudioLineage):
            service.append_event(
                _submit_command(
                    runtime_id=runtime.id,
                    student=other,
                    learning_session=learning_session,
                    scene=scene,
                    token_ids=list(current_token_ids),
                    idempotency_key="sentence-ordering-other-student",
                )
            )
        assert session.scalar(select(func.count()).select_from(CandidateEvent)) == 0
        assert session.scalar(select(func.count()).select_from(LearningEvidence)) == 0
        assert session.scalar(select(func.count()).select_from(PersonalFact)) == 0
        assert session.scalar(select(func.count()).select_from(StudioStudentInteraction)) == 2


def test_normal_tutor_turn_activates_only_exact_persisted_english_decision(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Removing the English exact adapter from the dispatcher must prevent this active Scene."""

    from services.platform.db.models import ModelTask

    class Provider:
        calls = 0

        def stream(self, route: ModelRoute, payload: dict[str, object]):
            del route, payload
            self.calls += 1
            yield StreamDelta("Let us put the words in order together.")
            yield StreamComplete(
                ModelResult(
                    output={
                        "text": "Let us put the words in order together.",
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
                        "workspace_intent": _english_intent().model_dump(mode="json"),
                    }
                )
            )

    with postgres_session_factory.begin() as session:
        student = _student(session, "english-normal-tutor")
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
                routes={ModelTask.TUTOR: ModelRoute("fixture", "english-sentence-ordering-tutor")},
                providers={"fixture": provider},
            ),
        )
        list(runtime.stream_turn(learning_session=learning_session, question="Can you help me order these words?"))

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
        assert scene.activity_key == "sentence_ordering_workspace"
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


def test_sentence_submission_keeps_source_truth_after_later_record_only_reorder(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing submitted source with the later Snapshot must break Tutor context assertions."""

    from apps.api.routes import student as student_routes
    from services.platform.db.models import ModelTask, StudioCanvasSpecialistRun
    from services.studio.subjects.sentence_ordering import (
        BIRDS_TOKEN_ID,
        CLOUDS_TOKEN_ID,
        FLY_TOKEN_ID,
        OVER_TOKEN_ID,
        REORDER_TOKEN_ACTION_KEY,
        SUBMIT_CONFIGURATION_ACTION_KEY,
    )

    valid_token_ids = [BIRDS_TOKEN_ID, FLY_TOKEN_ID, OVER_TOKEN_ID, CLOUDS_TOKEN_ID]
    changed_token_ids = [BIRDS_TOKEN_ID, OVER_TOKEN_ID, FLY_TOKEN_ID, CLOUDS_TOKEN_ID]

    class Provider:
        calls = 0

        def stream(self, route: ModelRoute, payload: dict[str, object]):
            del route
            self.calls += 1
            source_event = payload["studio_interaction_context"]["source"]["event"]
            source_state = source_event["action_payload"]
            source_validation = source_event["validation"]
            current_state = payload["studio_interaction_context"]["workspace"]["state"]["sentence_ordering_workspace"]
            selected_state = payload["studio_workspace_context"]["snapshot"]["state"]["sentence_ordering_workspace"]
            assert source_state == {"token_ids": valid_token_ids}
            assert source_validation == {
                "status": "VALID",
                "feedback_code": "SENTENCE_ORDER_COMPLETE",
                "next_action_keys": [],
            }
            assert current_state["token_ids"] == changed_token_ids
            assert current_state == selected_state
            yield StreamDelta("You put the words in sentence order.")
            yield StreamComplete(ModelResult(output={"text": "You put the words in sentence order.", "workspace_intent": None}))

    with postgres_session_factory.begin() as session:
        student = _student(session, "english-api")
        learning_session = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
        scene = service.accept_scene(_english_scene_command(student, learning_session))
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
            routes={ModelTask.TUTOR: ModelRoute("fixture", "english-sentence-ordering-continuation")},
            providers={"fixture": provider},
        ),
    )
    client = _client(postgres_session_factory, subject="english-api")
    try:
        reorder_birds = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id),
                "base_scene_version": scene_version,
                "action_key": REORDER_TOKEN_ACTION_KEY,
                "payload": {"token_id": BIRDS_TOKEN_ID, "from_index": 1, "to_index": 0},
                "idempotency_key": "api-sentence-ordering-birds",
            },
        )
        assert reorder_birds.status_code == 200 and reorder_birds.json()["student_interaction_id"] is None

        with postgres_session_factory.begin() as session:
            current_scene = session.get(StudioScene, scene_id)
            assert current_scene is not None
            current_scene_version = current_scene.scene_version
        reorder_fly = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id),
                "base_scene_version": current_scene_version,
                "action_key": REORDER_TOKEN_ACTION_KEY,
                "payload": {"token_id": FLY_TOKEN_ID, "from_index": 3, "to_index": 1},
                "idempotency_key": "api-sentence-ordering-fly",
            },
        )
        assert reorder_fly.status_code == 200 and reorder_fly.json()["student_interaction_id"] is None

        with postgres_session_factory.begin() as session:
            current_scene = session.get(StudioScene, scene_id)
            assert current_scene is not None
            current_scene_version = current_scene.scene_version
        reorder_over = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id),
                "base_scene_version": current_scene_version,
                "action_key": REORDER_TOKEN_ACTION_KEY,
                "payload": {"token_id": OVER_TOKEN_ID, "from_index": 3, "to_index": 2},
                "idempotency_key": "api-sentence-ordering-over",
            },
        )
        assert reorder_over.status_code == 200 and reorder_over.json()["student_interaction_id"] is None

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
                "payload": {"token_ids": valid_token_ids},
                "idempotency_key": "api-sentence-ordering-submit",
            },
        )
        assert submit.status_code == 200
        interaction_id = submit.json()["student_interaction_id"]
        assert interaction_id and submit.json()["student_interaction_status"] == "PENDING"

        with postgres_session_factory.begin() as session:
            current_scene = session.get(StudioScene, scene_id)
            interaction = session.get(StudioStudentInteraction, UUID(interaction_id))
            assert current_scene is not None and interaction is not None and interaction.status == "PENDING"
            submitted_scene_version = current_scene.scene_version
        later_reorder = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id),
                "base_scene_version": submitted_scene_version,
                "action_key": REORDER_TOKEN_ACTION_KEY,
                "payload": {"token_id": OVER_TOKEN_ID, "from_index": 2, "to_index": 1},
                "idempotency_key": "api-sentence-ordering-after-submit",
            },
        )
        assert later_reorder.status_code == 200 and later_reorder.json()["student_interaction_id"] is None

        stream = client.post(f"/api/v1/student/studio/{runtime_id}/interactions/{interaction_id}/turn/stream")
        assert stream.status_code == 200
        assert provider.calls == 1
        with postgres_session_factory.begin() as session:
            messages = list(session.scalars(select(LearningMessage).where(LearningMessage.session_id == learning_session_id)))
            assert [(message.role, message.content) for message in messages] == [
                ("tutor", "You put the words in sentence order.")
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
