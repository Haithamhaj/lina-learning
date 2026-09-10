"""Typed contract coverage for STUDIO-RUNTIME-01 model-facing Studio context."""

from __future__ import annotations

from uuid import uuid4


def test_studio_tutor_context_exposes_snapshot_and_ordered_semantic_events() -> None:
    """Tutor receives compact semantic Workspace state, never ORM row objects."""

    from services.studio.tutor_context import (
        StudioTutorEventContext,
        StudioTutorWorkspaceContext,
    )

    runtime_id = uuid4()
    context = StudioTutorWorkspaceContext(
        runtime_id=runtime_id,
        snapshot_schema_version="studio-snapshot-v1",
        through_sequence=4,
        snapshot_sequence=4,
        current_scene_id=None,
        current_scene_version=None,
        active_subject_key="MATH",
        active_activity_key=None,
        state_payload={"scene": "accepted"},
        unseen_events=(
            StudioTutorEventContext(
                sequence=4,
                actor="STUDENT",
                event_kind="fixture.step_submitted",
                action_key="SUBMIT_STEP",
                subject_key="MATH",
                activity_key="fixture_activity",
                base_scene_version=1,
                resulting_scene_version=2,
                payload_schema_version="fixture-action-v1",
                payload={"action": {"answer": "4"}, "validation": {"status": "INVALID"}},
            ),
        ),
        observation_id=uuid4(),
    )

    assert context.as_model_payload() == {
        "schema_version": "studio-tutor-context-v1",
        "through_sequence": 4,
        "snapshot": {
            "schema_version": "studio-snapshot-v1",
            "sequence": 4,
            "current_scene_id": None,
            "current_scene_version": None,
                "active_subject_key": "MATH",
                "active_activity_key": None,
                "current_scene_capability": None,
                "state": {"scene": "accepted"},
        },
        "unseen_events": [
            {
                "sequence": 4,
                "actor": "STUDENT",
                "event_kind": "fixture.step_submitted",
                "action_key": "SUBMIT_STEP",
                "subject_key": "MATH",
                "activity_key": "fixture_activity",
                "base_scene_version": 1,
                "resulting_scene_version": 2,
                "payload_schema_version": "fixture-action-v1",
                "payload": {"action": {"answer": "4"}, "validation": {"status": "INVALID"}},
            }
        ],
    }


def test_tutor_model_payload_includes_typed_studio_workspace_context() -> None:
    """Studio is additive deterministic input to the existing primary Tutor call."""

    from services.studio.tutor_context import StudioTutorWorkspaceContext
    from services.tutor.runtime import build_tutor_model_payload

    studio = StudioTutorWorkspaceContext(
        runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=0,
        snapshot_sequence=0, current_scene_id=None, current_scene_version=None,
        active_subject_key=None, active_activity_key=None, state_payload={}, unseen_events=(), observation_id=None,
    )

    payload = build_tutor_model_payload(question="Can you help me?", studio_context=studio)

    assert "Studio Workspace Context" in str(payload["input"])
    assert '"through_sequence": 0' in str(payload["input"])


def test_workspace_context_carries_exact_active_scene_capability_without_registry_dump() -> None:
    """Runtime-02 uses Scene-persisted versions rather than a latest capability guess."""

    from services.studio.tutor_context import (
        StudioTutorSceneCapability,
        StudioTutorWorkspaceContext,
    )

    context = StudioTutorWorkspaceContext(
        runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=0,
        snapshot_sequence=0, current_scene_id=uuid4(), current_scene_version=3,
        active_subject_key="MATH", active_activity_key="fraction_fixture", state_payload={}, unseen_events=(), observation_id=None,
        current_scene_capability=StudioTutorSceneCapability(
            scene_id=uuid4(), subject_key="MATH", subject_profile_version="subject-profile-v1",
            activity_key="fraction_fixture", activity_version="activity-v1", renderer_key="fraction-renderer",
            renderer_version="renderer-v1", allowed_action_keys=("SUBMIT",), source_references=("source-1",),
        ),
    )

    scene = context.as_model_payload()["snapshot"]["current_scene_capability"]
    assert scene["subject_profile_version"] == "subject-profile-v1"
    assert scene["allowed_action_keys"] == ["SUBMIT"]
    assert "renderer_key" not in scene


def test_agentic_canvas_context_exposes_only_semantic_projection_and_finite_action() -> None:
    """Active Canvas and Chat share meaning without renderer or raw state internals."""

    from services.studio.tutor_context import (
        StudioTutorEventContext,
        StudioTutorWorkspaceContext,
    )

    action = {
        "version": "agentic-canvas-action-v1",
        "action": "SELECT",
        "block_id": "decimal-line",
        "element_id": "decimal-a",
        "from_value": None,
        "to_value": None,
    }
    projection = {
        "version": "agentic-canvas-tutor-projection-v1",
        "scene_objective": "Compare decimals.",
        "subject": "MATH",
        "scene_status": "ACTIVE",
        "blocks": [],
        "current_focus": None,
        "recent_student_actions": [],
    }
    context = StudioTutorWorkspaceContext(
        runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=3,
        snapshot_sequence=3, current_scene_id=uuid4(), current_scene_version=2,
        active_subject_key="CANVAS", active_activity_key="agentic_canvas",
        state_payload={"scene_seed": {"provider_url": "must-not-reach-tutor"}},
        unseen_events=(StudioTutorEventContext(
            sequence=3, actor="STUDENT", event_kind="canvas.agentic.select", action_key="SELECT",
            subject_key="CANVAS", activity_key="agentic_canvas", base_scene_version=1,
            resulting_scene_version=2, payload_schema_version="agentic-canvas-action-v1",
            payload={"action": action, "validation": {"status": "VALID"}},
        ),), observation_id=uuid4(), visual_scene=projection,
    )

    payload = context.as_model_payload()

    assert payload["snapshot"]["state"] == {}
    assert payload["snapshot"]["visual_scene"] == projection
    assert payload["unseen_events"][0]["payload"] == {"action": action}
    assert "provider_url" not in str(payload)
