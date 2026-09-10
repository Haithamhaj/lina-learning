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
                        "accessibility": {"text_equivalent": "A number line for comparing decimals."},
                        "board_kind": "NUMBER_LINE",
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


def test_agentic_plan_uses_semantic_placements_not_browser_layout() -> None:
    from services.studio.agentic_canvas import AgenticCanvasPlanV1

    plan = AgenticCanvasPlanV1.model_validate({
        "version": "agentic-canvas-plan-v1", "objective": "Compare decimals.", "subject_key": "MATH",
        "layout": "FOCUS_SUPPORT", "palette": "WARM", "motion": "SUBTLE",
        "placements": [{"block_id": "line", "role": "PRIMARY", "order": 0, "span": "WIDE"}],
        "reveal_order": [],
    })
    assert plan.placements[0].role == "PRIMARY"
    with pytest.raises(ValueError):
        AgenticCanvasPlanV1.model_validate({**plan.model_dump(), "placements": [{"block_id": "line", "role": "PRIMARY", "order": 0, "x": 421}]})


def test_agentic_projection_is_semantic_and_rejects_browser_noise() -> None:
    from services.studio.agentic_canvas import AgenticCanvasActionV1, build_agentic_tutor_projection

    projection = build_agentic_tutor_projection(
        objective="Compare 0.6 and 0.45",
        subject_key="MATH",
        scene_status="ACTIVE",
        blocks=[{"block_id": "number-line-1", "type": "MATH_BOARD", "meaning": "Decimal comparison", "accessibility": {"text_equivalent": "A decimal number line."}, "board_kind": "NUMBER_LINE", "elements": [{"id": "decimal-a", "label": "0.6", "current_value": "0.6"}]}],
        actions=[AgenticCanvasActionV1.model_validate({"version": "agentic-canvas-action-v1", "action": "MOVE", "block_id": "number-line-1", "element_id": "decimal-a", "from_value": "0.6", "to_value": "0.65"})],
    )

    assert projection["recent_student_actions"][0]["to"] == "0.65"
    assert "renderer_key" not in str(projection)
    with pytest.raises(ValueError):
        AgenticCanvasActionV1.model_validate({"version": "agentic-canvas-action-v1", "action": "MOVE", "block_id": "number-line-1", "element_id": "decimal-a", "x": 421})
