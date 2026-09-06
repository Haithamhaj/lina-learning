"""Small guard that the Tutor context boundary remains a dedicated module."""

from pathlib import Path
from uuid import uuid4

from services.tutor import context
from services.tutor.context import TutorContextBuilder


def test_tutor_context_builder_module_exists() -> None:
    assert (Path(__file__).parents[1] / "services/tutor/context.py").exists()


def test_default_context_builder_constructs_hybrid_retrieval_with_embedding_gateway(
    monkeypatch,
) -> None:
    gateway = object()
    monkeypatch.setattr(context, "create_embedding_gateway", lambda session: gateway, raising=False)

    builder = TutorContextBuilder(object())

    assert builder._retrieval._embedding_gateway is gateway


def test_live_subject_context_is_explicit_or_unknown_never_session_derived() -> None:
    """Catches a legacy LearningSession default being repurposed as Daily subject authority."""

    legacy = context.legacy_math_live_subject()
    unknown = context.unknown_live_subject()
    english_canvas = context.studio_scene_live_subject(
        subject_key="ENGLISH",
        origin=context.LiveSubjectOrigin.CANVAS_SCENE,
    )

    assert legacy.broad_subject == "MATH"
    assert legacy.origin is context.LiveSubjectOrigin.LEGACY_MATH_ENTRY
    assert unknown.broad_subject is None
    assert unknown.origin is context.LiveSubjectOrigin.UNKNOWN
    assert english_canvas.broad_subject == "LANGUAGE_ARTS"
    assert english_canvas.origin is context.LiveSubjectOrigin.CANVAS_SCENE


def test_chat_uses_a_scene_subject_only_for_an_exact_server_link() -> None:
    """Catches free-form Chat inheriting an active Workspace subject without source proof."""

    from services.studio.tutor_context import StudioTutorSceneCapability, StudioTutorWorkspaceContext

    source_message_id = uuid4()
    workspace = StudioTutorWorkspaceContext(
        runtime_id=uuid4(),
        snapshot_schema_version="studio-snapshot-v1",
        through_sequence=0,
        snapshot_sequence=0,
        current_scene_id=uuid4(),
        current_scene_version=1,
        active_subject_key="ENGLISH",
        active_activity_key="sentence_ordering_workspace",
        state_payload={},
        unseen_events=(),
        observation_id=None,
        current_scene_capability=StudioTutorSceneCapability(
            scene_id=uuid4(),
            subject_key="ENGLISH",
            subject_profile_version="subject-profile-v2",
            activity_key="sentence_ordering_workspace",
            activity_version="sentence-ordering-workspace-activity-v1",
            renderer_key="sentence-ordering-workspace",
            renderer_version="sentence-ordering-workspace-renderer-v1",
            allowed_action_keys=(),
            source_references=(),
            source_message_id=source_message_id,
        ),
    )

    linked = context.linked_scene_live_subject(
        studio_context=workspace,
        source_tutor_message_id=source_message_id,
    )
    unlinked = context.linked_scene_live_subject(
        studio_context=workspace,
        source_tutor_message_id=uuid4(),
    )

    assert linked.broad_subject == "LANGUAGE_ARTS"
    assert linked.origin is context.LiveSubjectOrigin.CHAT_LINKED_SCENE
    assert unlinked == context.unknown_live_subject()
