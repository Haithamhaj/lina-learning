from __future__ import annotations

import pytest


def test_agentic_scene_accepts_only_declarative_allowlisted_blocks() -> None:
    from services.studio.agentic_canvas import AgenticCanvasSceneV1

    scene = AgenticCanvasSceneV1.model_validate(
        {
            "version": "agentic-canvas-scene-v1",
            "objective": "Compare the decimals.",
            "subject_key": "MATH",
            "blocks": [
                {
                    "block_id": "number-line-1",
                    "type": "MATH_BOARD",
                    "meaning": "Compare decimal locations.",
                    "elements": [{"id": "decimal-a", "label": "0.6", "current_value": "0.6"}],
                }
            ],
        }
    )

    assert scene.blocks[0].block_id == "number-line-1"
    with pytest.raises(ValueError):
        AgenticCanvasSceneV1.model_validate({**scene.model_dump(), "blocks": [{"block_id": "x", "type": "SCRIPT", "code": "alert(1)"}]})


def test_agentic_scene_requires_explicit_nullable_values_for_strict_model_output() -> None:
    from pydantic import ValidationError
    from services.studio.agentic_canvas import AgenticCanvasSceneV1

    payload = {
        "version": "agentic-canvas-scene-v1",
        "objective": "Compare fractions.",
        "subject_key": "MATH",
        "blocks": [{"block_id": "fraction-board", "type": "MATH_BOARD", "meaning": "Compare equal parts.", "elements": [{"id": "whole", "label": "Whole"}]}],
    }

    with pytest.raises(ValidationError, match="current_value"):
        AgenticCanvasSceneV1.model_validate(payload)


def test_agentic_projection_is_semantic_and_rejects_browser_noise() -> None:
    from services.studio.agentic_canvas import AgenticCanvasActionV1, build_agentic_tutor_projection

    projection = build_agentic_tutor_projection(
        objective="Compare 0.6 and 0.45",
        subject_key="MATH",
        scene_status="ACTIVE",
        blocks=[{"block_id": "number-line-1", "type": "MATH_BOARD", "meaning": "Decimal comparison", "elements": [{"id": "decimal-a", "label": "0.6", "current_value": "0.6"}]}],
        actions=[AgenticCanvasActionV1.model_validate({"version": "agentic-canvas-action-v1", "action": "MOVE", "block_id": "number-line-1", "element_id": "decimal-a", "from_value": "0.6", "to_value": "0.65"})],
    )

    assert projection["recent_student_actions"][0]["to"] == "0.65"
    assert "renderer_key" not in str(projection)
    with pytest.raises(ValueError):
        AgenticCanvasActionV1.model_validate({"version": "agentic-canvas-action-v1", "action": "MOVE", "block_id": "number-line-1", "element_id": "decimal-a", "x": 421})
