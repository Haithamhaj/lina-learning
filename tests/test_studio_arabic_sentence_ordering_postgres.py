"""Arabic ordering persistence coverage using the real Studio service."""

from __future__ import annotations

import os
from uuid import UUID

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.platform.db.models import LearningMessage, LearningSegment, LearningSession, StudioScene, Student, User
from services.studio.contracts import AppendStudioEventCommand, CreateSceneCommand, StudioActor
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import StaleSceneVersion, StudioStateError, StudioStateService
from services.studio.subjects.arabic_sentence_ordering import (
    ACTIVITY_KEY, ACTIVITY_VERSION, ACCESSIBILITY_PAYLOAD, ARABIC_PROFILE_VERSION,
    LESSON_TOKEN_ID, RENDERER_KEY, RENDERER_VERSION, REORDER_PAYLOAD_SCHEMA_VERSION,
    REORDER_TOKEN_ACTION_KEY, SCENE_PAYLOAD_SCHEMA_VERSION, STUDENT_TOKEN_ID,
    SUBMIT_CONFIGURATION_ACTION_KEY, SUBMIT_PAYLOAD_SCHEMA_VERSION, VERB_TOKEN_ID,
    arabic_sentence_ordering_scene_seed,
)


@pytest.fixture
def db_session() -> Session:
    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(normalize_database_url(database_url))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE studio_canvas_specialist_runs, studio_tutor_observations, studio_student_interactions, studio_events, studio_snapshots, studio_scenes, studio_runtimes, learning_messages, learning_segments, learning_sessions, students, users CASCADE"))
    session = sessionmaker(engine, expire_on_commit=False)()
    try:
        yield session
        session.commit()
    finally:
        session.close(); engine.dispose()


def _student(session: Session, name: str) -> Student:
    user = User(identity_provider="clerk", external_subject=name, email=f"{name}@example.test", role="STUDENT")
    session.add(user); session.flush()
    student = Student(user_id=user.id, display_name=name)
    session.add(student); session.flush()
    return student


def _session(session: Session, student: Student) -> LearningSession:
    value = LearningSession(student_id=student.id, subject="ARABIC", status="OPEN")
    session.add(value); session.flush()
    return value


def _scene_command(student: Student, learning_session: LearningSession) -> CreateSceneCommand:
    return CreateSceneCommand(
        student_id=student.id, learning_session_id=learning_session.id, subject_key="ARABIC", subject_profile_version=ARABIC_PROFILE_VERSION,
        concept_keys=("sentence-order",), activity_key=ACTIVITY_KEY, artifact_type="interactive-activity", renderer_key=RENDERER_KEY,
        renderer_version=RENDERER_VERSION, activity_contract_version=ACTIVITY_VERSION, payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
        seed_payload=arabic_sentence_ordering_scene_seed(), accessibility_payload=ACCESSIBILITY_PAYLOAD, locale="ar", direction="rtl",
    )


def _command(*, runtime_id: UUID, student: Student, learning_session: LearningSession, scene: StudioScene, action: str, payload: dict[str, object], key: str, version: int | None = None) -> AppendStudioEventCommand:
    schema = REORDER_PAYLOAD_SCHEMA_VERSION if action == REORDER_TOKEN_ACTION_KEY else SUBMIT_PAYLOAD_SCHEMA_VERSION
    return AppendStudioEventCommand(
        runtime_id=runtime_id, student_id=student.id, learning_session_id=learning_session.id, event_kind=None, event_schema_version=None,
        actor=StudioActor.STUDENT, action_key=action, payload_schema_version=schema, payload=payload, scene_id=scene.id,
        base_scene_version=scene.scene_version if version is None else version, idempotency_key=key,
    )


def test_arabic_scene_persists_rebuilds_and_rejects_mismatched_operations(db_session: Session) -> None:
    student = _student(db_session, "arabic-state")
    learning_session = _session(db_session, student)
    service = StudioStateService(db_session)
    runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning_session.id)
    scene = service.accept_scene(_scene_command(student, learning_session))
    service.append_event(AppendStudioEventCommand(runtime_id=runtime.id, student_id=student.id, learning_session_id=learning_session.id, event_kind="studio.scene.activated", event_schema_version=CORE_EVENT_SCHEMA_VERSION, actor=StudioActor.SYSTEM, payload_schema_version="studio-scene-activated-v1", payload={}, scene_id=scene.id, base_scene_version=scene.scene_version, idempotency_key="activate-arabic"))

    first = _command(runtime_id=runtime.id, student=student, learning_session=learning_session, scene=scene, action=REORDER_TOKEN_ACTION_KEY, payload={"token_id": VERB_TOKEN_ID, "from_index": 2, "to_index": 0}, key="arabic-reorder")
    appended = service.append_event(first)
    assert appended.interaction is None
    assert service.append_event(first).replayed is True
    snapshot = service.runtime_state(runtime_id=runtime.id, student_id=student.id)["snapshot"]
    assert snapshot["state_payload"][ACTIVITY_KEY]["token_ids"] == [VERB_TOKEN_ID, STUDENT_TOKEN_ID, LESSON_TOKEN_ID]
    assert service.rebuild_snapshot(runtime_id=runtime.id, student_id=student.id) == snapshot

    submitted = service.append_event(_command(runtime_id=runtime.id, student=student, learning_session=learning_session, scene=scene, action=SUBMIT_CONFIGURATION_ACTION_KEY, payload={"token_ids": [VERB_TOKEN_ID, STUDENT_TOKEN_ID, LESSON_TOKEN_ID]}, key="arabic-submit"))
    assert submitted.interaction is not None
    assert submitted.event.payload["validation"]["status"] == "VALID"
    before = service.runtime_state(runtime_id=runtime.id, student_id=student.id)
    for payload in ({"token_id": "unknown", "from_index": 0, "to_index": 1}, {"token_ids": [VERB_TOKEN_ID, VERB_TOKEN_ID, LESSON_TOKEN_ID]}, {"token_ids": [VERB_TOKEN_ID, STUDENT_TOKEN_ID]}):
        action = REORDER_TOKEN_ACTION_KEY if "token_id" in payload else SUBMIT_CONFIGURATION_ACTION_KEY
        with pytest.raises(StudioStateError):
            service.append_event(_command(runtime_id=runtime.id, student=student, learning_session=learning_session, scene=scene, action=action, payload=payload, key=f"reject-{action}-{len(payload)}"))
    assert service.runtime_state(runtime_id=runtime.id, student_id=student.id) == before
    with pytest.raises(StaleSceneVersion):
        service.append_event(_command(runtime_id=runtime.id, student=student, learning_session=learning_session, scene=scene, action=REORDER_TOKEN_ACTION_KEY, payload={"token_id": LESSON_TOKEN_ID, "from_index": 2, "to_index": 1}, key="stale", version=scene.scene_version - 1))


def test_arabic_exact_activation_retains_lineage_and_progress(db_session):
    from services.studio.arabic_sentence_ordering_activation import activate_arabic_sentence_ordering_from_workspace_decision as activate
    from services.studio.router import route_workspace_intent, WorkspaceAuthorityContext
    from services.studio.workspace_intent import WorkspaceIntent
    from services.studio.subjects import production_subject_registry, PRODUCTION_CURRENT_PROFILE_VERSIONS
    student = _student(db_session, "arabic-activation")
    ls = _session(db_session, student)
    segment = LearningSegment(session_id=ls.id, sequence=1)
    db_session.add(segment); db_session.flush()
    source = LearningMessage(session_id=ls.id, segment_id=segment.id, role="tutor", content="رتّب الكلمات.")
    db_session.add(source); db_session.flush()
    intent = WorkspaceIntent.model_validate(dict(version="workspace-intent-v1", action="OPEN_ACTIVITY", subject_key="ARABIC", concept_keys=["sentence-order"], learning_goal="Arrange the declared verb-initial sentence.", activity_hint=ACTIVITY_KEY, representation_need="INTERACTIVE", expected_student_response_mode="WORKSPACE", presentation_sequence="PARALLEL", source_references=[], safe_text_fallback="رتّب الكلمات."))
    decision = route_workspace_intent(intent, WorkspaceAuthorityContext(registry=production_subject_registry(), current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS))
    audit = {"intent_status":"VALID", "intent":intent.model_dump(mode="json"), "decision":decision.as_audit_payload()}
    kwargs = dict(learning_session=ls,source_tutor_message=source,source_segment_id=segment.id)
    assert activate(db_session,**kwargs,workspace_audit={**audit,"decision":{**audit["decision"],"selected_renderer_version":"unknown"}}) is None
    scene = activate(db_session,**kwargs,workspace_audit=audit)
    assert scene.status == "ACTIVE" and scene.source_message_id == source.id and scene.source_segment_id == segment.id
    service = StudioStateService(db_session)
    runtime = service.get_or_create_runtime(student_id=student.id,learning_session_id=ls.id)
    service.append_event(_command(runtime_id=runtime.id,student=student,learning_session=ls,scene=scene,action=REORDER_TOKEN_ACTION_KEY,payload={"token_id":VERB_TOKEN_ID,"from_index":2,"to_index":0},key="progress"))
    before = service.runtime_state(runtime_id=runtime.id,student_id=student.id)
    assert activate(db_session,**kwargs,workspace_audit=audit).id == scene.id
    assert service.runtime_state(runtime_id=runtime.id,student_id=student.id) == before
    db_session.commit()
    db_session.expire_all()
    assert service.runtime_state(runtime_id=runtime.id,student_id=student.id) == before
    assert service.rebuild_snapshot(runtime_id=runtime.id,student_id=student.id) == before["snapshot"]
