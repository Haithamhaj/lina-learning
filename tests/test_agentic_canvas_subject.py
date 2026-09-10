from __future__ import annotations

from uuid import uuid4

import pytest

from services.studio.reducer import ReducerEvent, reduce_snapshot
from services.studio.subjects import production_subject_registry


def _scene() -> dict[str, object]:
    return {
        "version": "agentic-canvas-scene-v1",
        "objective": "Compare the quantities.",
        "subject_key": "MATH",
        "blocks": [
            {
                "block_id": "number-line",
                "type": "MATH_BOARD",
                "meaning": "Compare exact positions.",
                "title": "Number line",
                "accessibility": {"text_equivalent": "An exact number line.", "aria_label": None},
                "allowed_actions": ["FOCUS", "SET_VALUE"],
                "elements": [{"id": "point-a", "label": "Point A", "current_value": "3/5"}],
                "board_kind": "NUMBER_LINE",
                "axis_min": "0",
                "axis_max": "1",
            }
        ],
    }


def _snapshot(scene_id, scene: dict[str, object]) -> dict[str, object]:
    return {
        "snapshot_schema_version": "studio-snapshot-v1",
        "latest_event_sequence": 2,
        "current_scene_id": scene_id,
        "current_scene_version": 2,
        "active_subject_key": "CANVAS",
        "active_activity_key": "agentic_canvas",
        "active_step_key": None,
        "last_meaningful_student_event_id": None,
        "state_payload": {"scene_seed": scene, "scene_status": "ACTIVE"},
    }


def _event(scene_id, payload: dict[str, object]) -> ReducerEvent:
    return ReducerEvent(
        id=uuid4(), sequence=3, event_kind="canvas.agentic.set_value",
        action_key="SET_VALUE", event_schema_version="agentic-canvas-action-event-v1",
        actor="STUDENT", scene_id=scene_id, base_scene_version=2,
        resulting_scene_version=3, subject_key="CANVAS", activity_key="agentic_canvas",
        payload=payload, activity_contract_version="agentic-canvas-activity-v1",
        subject_profile_version="agentic-canvas-profile-v1",
        payload_schema_version="agentic-canvas-action-v1",
    )


def test_registered_agentic_activity_validates_and_reduces_current_semantic_state() -> None:
    registry = production_subject_registry()
    scene = _scene()
    registry.validate_scene(
        subject_key="CANVAS", subject_profile_version="agentic-canvas-profile-v1",
        activity_key="agentic_canvas", activity_version="agentic-canvas-activity-v1",
        renderer_key="agentic-canvas", renderer_version="agentic-canvas-renderer-v1",
        payload_schema_version="agentic-canvas-scene-v1", seed_payload=scene,
        locale="en", direction="ltr",
    )
    action = registry.resolve_action(
        "CANVAS", "agentic-canvas-profile-v1", "agentic_canvas",
        "agentic-canvas-activity-v1", "SET_VALUE",
    )
    assert action.payload_schema_version == "agentic-canvas-action-v1"
    assert action.interaction_policy.value == "TUTOR_TRIGGERING"

    scene_id = uuid4()
    payload = {
        "version": "agentic-canvas-action-v1", "action": "SET_VALUE",
        "block_id": "number-line", "element_id": "point-a",
        "from_value": "3/5", "to_value": "4/5",
    }
    reduced = reduce_snapshot(_snapshot(scene_id, scene), _event(scene_id, payload), subject_registry=registry)
    assert reduced["state_payload"]["agentic_canvas"]["blocks"][0]["elements"][0]["current_value"] == "4/5"
    assert reduced["current_scene_version"] == 3


def test_registered_agentic_activity_rejects_unknown_or_disallowed_semantics() -> None:
    registry = production_subject_registry()
    scene_id = uuid4()
    payload = {
        "version": "agentic-canvas-action-v1", "action": "SET_VALUE",
        "block_id": "number-line", "element_id": "unknown",
        "from_value": "3/5", "to_value": "4/5",
    }
    with pytest.raises(ValueError, match="semantic|rejected|unknown"):
        reduce_snapshot(_snapshot(scene_id, _scene()), _event(scene_id, payload), subject_registry=registry)

    payload["action"] = "MOVE"
    event = _event(scene_id, payload)
    event = ReducerEvent(**{**event.__dict__, "action_key": "MOVE"})
    with pytest.raises(ValueError, match="semantic|rejected|allowed"):
        reduce_snapshot(_snapshot(scene_id, _scene()), event, subject_registry=registry)

    mismatched = _event(scene_id, {**payload, "action": "FOCUS", "element_id": "point-a", "from_value": None, "to_value": None})
    with pytest.raises(ValueError, match="payload|contract"):
        reduce_snapshot(_snapshot(scene_id, _scene()), mismatched, subject_registry=registry)
