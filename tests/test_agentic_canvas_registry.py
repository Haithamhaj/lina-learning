from __future__ import annotations

import pytest

from services.studio.agent.tools import create_math_board


def test_run_local_registry_accepts_only_tool_created_blocks_in_final_scene() -> None:
    from services.studio.agent.registry import CanvasBlockRegistry
    from services.studio.agentic_canvas import AgenticCanvasSceneV1

    registry = CanvasBlockRegistry()
    block = create_math_board(
        block_id="fraction-board",
        meaning="Compare equal parts of one whole.",
        label="Fraction comparison",
        expression="3/4 + 1/8",
    )
    registry.accept(block)
    scene = AgenticCanvasSceneV1(
        version="agentic-canvas-scene-v1",
        objective="Compare fractions.",
        subject_key="MATH",
        blocks=[block],
    )

    registry.validate_scene(scene)

    fabricated = scene.model_copy(update={"blocks": [block.model_copy(update={"block_id": "invented"})]})
    with pytest.raises(ValueError, match="not produced by a registered tool"):
        registry.validate_scene(fabricated)


def test_materialized_plan_preserves_durable_presentation_without_learner_context() -> None:
    """The Agent's semantic composition choices must reach the Scene contract."""
    from services.studio.agent.registry import CanvasBlockRegistry
    from services.studio.agent.tools import create_math_board
    from services.studio.agentic_canvas import AgenticCanvasPlanV1

    registry = CanvasBlockRegistry()
    block = registry.accept(create_math_board(
        block_id="number-line", meaning="Compare exact positions.", label="Number line",
        board_kind="NUMBER_LINE", axes=[{"axis": "X", "minimum": "0", "maximum": "1", "step": "1/10"}],
    ))
    scene = registry.materialize_plan(AgenticCanvasPlanV1.model_validate({
        "version": "agentic-canvas-plan-v1", "objective": "Compare decimals.", "subject_key": "MATH",
        "layout": "FOCUS_SUPPORT", "palette": "COOL", "motion": "REVEAL",
        "placements": [{"block_id": block.block_id, "role": "PRIMARY", "order": 0, "span": "FULL"}],
        "reveal_order": [block.block_id],
    }))

    assert scene.version == "agentic-canvas-scene-v2"
    assert scene.presentation.model_dump() == {
        "layout": "FOCUS_SUPPORT", "palette": "COOL", "motion": "REVEAL",
        "placements": [{"block_id": "number-line", "role": "PRIMARY", "order": 0, "span": "FULL"}],
        "reveal_order": ["number-line"],
    }
    assert "learner" not in scene.model_dump_json().casefold()
