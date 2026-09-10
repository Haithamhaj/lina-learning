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
