"""Exact normal-Tutor activation adapter for English sentence ordering."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import LearningMessage, LearningSession, StudioScene
from services.studio.contracts import AppendStudioEventCommand, CreateSceneCommand, StudioActor
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import InvalidStudioLineage, StudioStateError, StudioStateService
from services.studio.subjects.sentence_ordering import (
    ACTIVITY_KEY,
    ACTIVITY_VERSION,
    ACCESSIBILITY_PAYLOAD,
    ENGLISH_PROFILE_VERSION,
    RENDERER_KEY,
    RENDERER_VERSION,
    SCENE_PAYLOAD_SCHEMA_VERSION,
    sentence_ordering_scene_seed,
)


logger = logging.getLogger(__name__)


def activate_sentence_ordering_from_workspace_decision(
    session: Session,
    *,
    learning_session: LearningSession,
    source_tutor_message: LearningMessage,
    source_segment_id: UUID | None,
    workspace_audit: Mapping[str, object] | None,
) -> StudioScene | None:
    """Activate only the exact persisted English route emitted by the normal Tutor call."""

    if not _is_exact_sentence_ordering_open(workspace_audit):
        return None
    if (
        source_tutor_message.role != "tutor"
        or source_tutor_message.session_id != learning_session.id
        or source_tutor_message.segment_id != source_segment_id
    ):
        logger.warning("English sentence-ordering activation skipped because Tutor lineage is inconsistent.")
        return None
    try:
        state = StudioStateService(session)
        runtime = state.get_or_create_runtime(
            student_id=learning_session.student_id,
            learning_session_id=learning_session.id,
        )
        active_scene = session.execute(
            select(StudioScene)
            .where(StudioScene.studio_runtime_id == runtime.id, StudioScene.status == "ACTIVE")
            .with_for_update()
        ).scalar_one_or_none()
        if active_scene is not None:
            return active_scene if _is_sentence_ordering_scene(active_scene) else None
        accepted_scene = session.execute(
            select(StudioScene)
            .where(
                StudioScene.studio_runtime_id == runtime.id,
                StudioScene.student_id == learning_session.student_id,
                StudioScene.learning_session_id == learning_session.id,
                StudioScene.status == "ACCEPTED",
                StudioScene.source_message_id == source_tutor_message.id,
                StudioScene.source_segment_id == source_segment_id,
                StudioScene.subject_key == "ENGLISH",
                StudioScene.subject_profile_version == ENGLISH_PROFILE_VERSION,
                StudioScene.activity_key == ACTIVITY_KEY,
                StudioScene.activity_contract_version == ACTIVITY_VERSION,
                StudioScene.renderer_key == RENDERER_KEY,
                StudioScene.renderer_version == RENDERER_VERSION,
                StudioScene.payload_schema_version == SCENE_PAYLOAD_SCHEMA_VERSION,
            )
            .with_for_update()
        ).scalar_one_or_none()
        scene = accepted_scene or state.accept_scene(
            CreateSceneCommand(
                student_id=learning_session.student_id,
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
                source_message_id=source_tutor_message.id,
            )
        )
        if scene.status == "ACCEPTED":
            state.append_event(
                AppendStudioEventCommand(
                    runtime_id=runtime.id,
                    student_id=learning_session.student_id,
                    learning_session_id=learning_session.id,
                    event_kind="studio.scene.activated",
                    event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                    actor=StudioActor.SYSTEM,
                    payload_schema_version="studio-scene-activated-v1",
                    payload={},
                    scene_id=scene.id,
                    base_scene_version=scene.scene_version,
                    source_message_id=source_tutor_message.id,
                    source_segment_id=source_segment_id,
                    idempotency_key=f"sentence-ordering-activate:{source_tutor_message.id}",
                )
            )
        return scene
    except (InvalidStudioLineage, StudioStateError, ValueError):
        logger.warning("English sentence-ordering activation did not mutate Studio state safely.", exc_info=True)
        return None


def _is_exact_sentence_ordering_open(workspace_audit: Mapping[str, object] | None) -> bool:
    if not isinstance(workspace_audit, Mapping) or workspace_audit.get("intent_status") != "VALID":
        return False
    intent = workspace_audit.get("intent")
    decision = workspace_audit.get("decision")
    if not isinstance(intent, Mapping) or not isinstance(decision, Mapping):
        return False
    return (
        intent.get("action") == "OPEN_ACTIVITY"
        and intent.get("subject_key") == "ENGLISH"
        and intent.get("activity_hint") == ACTIVITY_KEY
        and decision.get("status") == "ROUTED"
        and decision.get("mode") == "KNOWN_INTERACTIVE"
        and decision.get("reason_code") == "EXACT_KNOWN_CAPABILITY"
        and decision.get("selected_subject_key") == "ENGLISH"
        and decision.get("selected_profile_version") == ENGLISH_PROFILE_VERSION
        and decision.get("selected_activity_key") == ACTIVITY_KEY
        and decision.get("selected_activity_version") == ACTIVITY_VERSION
        and decision.get("selected_renderer_key") == RENDERER_KEY
        and decision.get("selected_renderer_version") == RENDERER_VERSION
    )


def _is_sentence_ordering_scene(scene: StudioScene) -> bool:
    return (
        scene.subject_key == "ENGLISH"
        and scene.subject_profile_version == ENGLISH_PROFILE_VERSION
        and scene.activity_key == ACTIVITY_KEY
        and scene.activity_contract_version == ACTIVITY_VERSION
        and scene.renderer_key == RENDERER_KEY
        and scene.renderer_version == RENDERER_VERSION
    )
