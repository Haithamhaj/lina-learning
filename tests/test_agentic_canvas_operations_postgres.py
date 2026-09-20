"""Authenticated Agentic Canvas operation admission and durable current-state proof."""

from __future__ import annotations

import os

import pytest

from test_studio_make_ten_postgres import (
    _activate,
    _clear_overrides,
    _client,
    _learning_session,
    _student,
    postgres_session_factory,  # noqa: F401 - imported pytest fixture
)
from services.studio.contracts import CreateSceneCommand
from services.studio.service import StudioStateService
from services.studio.tutor_context import select_studio_tutor_context


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Disposable PostgreSQL DATABASE_URL is required for Agentic Canvas operations",
)


def _scene() -> dict[str, object]:
    return {
        "version": "agentic-canvas-scene-v2",
        "objective": "Compare the quantities.",
        "subject_key": "MATH",
        "presentation": {"layout": "FOCUS", "palette": "COOL", "motion": "NONE", "placements": [{"block_id": "number-line", "role": "PRIMARY", "order": 0, "span": "FULL"}], "reveal_order": []},
        "blocks": [{
            "block_id": "number-line", "type": "MATH_BOARD",
            "meaning": "Compare exact positions.", "title": "Number line",
            "accessibility": {"text_equivalent": "An exact number line.", "aria_label": None},
            "allowed_actions": ["SET_VALUE"],
            "elements": [{"id": "point-a", "label": "Point A", "current_value": "3/5"}],
            "board_kind": "NUMBER_LINE", "axis_min": "0", "axis_max": "1",
        }],
    }


def test_authenticated_agentic_operation_accepts_known_semantics_and_rejects_unknown_element(
    postgres_session_factory,  # noqa: F811 - pytest injects the imported fixture
) -> None:
    with postgres_session_factory.begin() as session:
        student = _student(session, "agentic-operation")
        learning = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning.id)
        scene = service.accept_scene(CreateSceneCommand(
            student_id=student.id, learning_session_id=learning.id,
            subject_key="CANVAS", subject_profile_version="agentic-canvas-profile-v2",
            concept_keys=("fraction-comparison",), activity_key="agentic_canvas",
            artifact_type="agentic-canvas", renderer_key="agentic-canvas",
            renderer_version="agentic-canvas-renderer-v2",
            activity_contract_version="agentic-canvas-activity-v1",
            payload_schema_version="agentic-canvas-scene-v2", seed_payload=_scene(),
            accessibility_payload={"text_equivalent": "An exact number line."},
            locale="en", direction="ltr",
        ))
        _activate(service, runtime_id=runtime.id, student=student, learning_session=learning, scene=scene)
        runtime_id, scene_id, scene_version = runtime.id, scene.id, scene.scene_version

    client = _client(postgres_session_factory, subject="agentic-operation")
    try:
        def operation(element_id: str, nonce: str):
            return client.post(
                f"/api/v1/student/studio/{runtime_id}/operations",
                json={
                    "scene_id": str(scene_id), "base_scene_version": scene_version,
                    "action_key": "SET_VALUE", "idempotency_key": nonce,
                    "payload": {
                        "version": "agentic-canvas-action-v1", "action": "SET_VALUE",
                        "block_id": "number-line", "element_id": element_id,
                        "from_value": "3/5", "to_value": "4/5",
                    },
                },
            )

        rejected = operation("unknown", "agentic-unknown")
        assert rejected.status_code == 422
        accepted = operation("point-a", "agentic-set-value")
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["student_interaction_status"] == "PENDING"
        snapshot = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot").json()
        assert snapshot["state_payload"]["agentic_canvas"]["blocks"][0]["elements"][0]["current_value"] == "4/5"
    finally:
        _clear_overrides()


def test_classification_move_reaches_tutor_as_learner_state_without_losing_solution_semantics(
    postgres_session_factory,  # noqa: F811
) -> None:
    scene_seed = {
        "version": "agentic-canvas-scene-v2", "objective": "Classify the slopes.", "subject_key": "MATH",
        "presentation": {"layout": "STACK", "palette": "COOL", "motion": "NONE", "placements": [{"block_id": "classify", "role": "INTERACTION", "order": 0, "span": "FULL"}], "reveal_order": []},
        "blocks": [{
            "block_id": "classify", "type": "TEXT_INTERACTION", "meaning": "Classify each line by slope.",
            "title": "Slope groups", "accessibility": {"text_equivalent": "Two slope categories.", "aria_label": None},
            "allowed_actions": ["MOVE"],
            "elements": [
                {"id": "steep", "label": "Steep line", "current_value": None},
                {"id": "gentle", "label": "Gentle line", "current_value": None},
                {"id": "fastest", "label": "Fastest", "current_value": None},
                {"id": "not-fastest", "label": "Not fastest", "current_value": None},
            ],
            "interaction_family": "CLASSIFICATION", "prompt": "Place one line.",
            "items": [
                {"id": "steep", "text": "Steep line", "group_id": "fastest"},
                {"id": "gentle", "text": "Gentle line", "group_id": "not-fastest"},
            ],
            "groups": [{"id": "fastest", "label": "Fastest"}, {"id": "not-fastest", "label": "Not fastest"}],
            "relations": [],
        }],
    }
    with postgres_session_factory.begin() as session:
        student = _student(session, "agentic-classification-state")
        learning = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning.id)
        scene = service.accept_scene(CreateSceneCommand(
            student_id=student.id, learning_session_id=learning.id, subject_key="CANVAS",
            subject_profile_version="agentic-canvas-profile-v2", concept_keys=("linear-slope",),
            activity_key="agentic_canvas", artifact_type="agentic-canvas", renderer_key="agentic-canvas",
            renderer_version="agentic-canvas-renderer-v2", activity_contract_version="agentic-canvas-activity-v1",
            payload_schema_version="agentic-canvas-scene-v2", seed_payload=scene_seed,
            accessibility_payload={"text_equivalent": "Classify two lines."}, locale="en", direction="ltr",
        ))
        _activate(service, runtime_id=runtime.id, student=student, learning_session=learning, scene=scene)
        runtime_id, scene_id, scene_version = runtime.id, scene.id, scene.scene_version
        student_id, learning_id = student.id, learning.id

    client = _client(postgres_session_factory, subject="agentic-classification-state")
    try:
        response = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id), "base_scene_version": scene_version,
                "action_key": "MOVE", "idempotency_key": "classify-steep",
                "payload": {"version": "agentic-canvas-action-v1", "action": "MOVE", "block_id": "classify", "element_id": "steep", "from_value": None, "to_value": "fastest"},
            },
        )
        assert response.status_code == 200, response.text
    finally:
        _clear_overrides()

    selection = select_studio_tutor_context(
        bind=postgres_session_factory.kw["bind"], student_id=student_id, learning_session_id=learning_id,
    )
    assert selection is not None
    visual = selection.context.as_model_payload()["snapshot"]["visual_scene"]
    block = visual["blocks"][0]
    assert next(item for item in block["elements"] if item["id"] == "steep")["current_value"] == "fastest"
    assert block["solution_semantics"]["item_group_assignments"][0] == {"item_id": "steep", "group_id": "fastest"}
    assert visual["recent_student_actions"][-1]["to"] == "fastest"
