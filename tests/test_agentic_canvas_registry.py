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


def test_image_and_custom_visual_share_one_v3_agent_plan() -> None:
    from services.studio.agent.registry import CanvasBlockRegistry
    from services.studio.agent.orchestrator import HostedGeneratedImage, _generated_image_block
    from services.studio.agentic_canvas import AgenticCanvasPlanV1, CustomVisualBlockV1, GeneratedImagePlanV1

    registry = CanvasBlockRegistry()
    registry.accept(_generated_image_block(GeneratedImagePlanV1(
        meaning="A young plant with roots below soil.", title="Plant illustration",
        text_equivalent="Two leaves above soil and visible roots beneath it."
    ), HostedGeneratedImage(temporary_handle="image-call-1", content=b"fixture")))
    registry.accept(CustomVisualBlockV1.model_validate({
        "block_id": "growth-control", "type": "CUSTOM_VISUAL", "meaning": "Step through seed growth.",
        "title": "Growth stages", "accessibility": {"text_equivalent": "Growth stages control."},
        "allowed_actions": [], "elements": [], "artifact_instance_id": "growth-instance",
        "bridge_nonce": "nonce1234", "custom_visual_build_id": "11111111-1111-4111-8111-111111111111",
        "manifest_digest": "a" * 64,
    }))
    plan = AgenticCanvasPlanV1.model_validate({
        "version": "agentic-canvas-plan-v1", "objective": "Explore growth.", "subject_key": "SCIENCE",
        "layout": "FOCUS_SUPPORT", "palette": "NATURE", "motion": "NONE",
        "placements": [
            {"block_id": "generated-image", "role": "PRIMARY", "order": 0, "span": "WIDE"},
            {"block_id": "growth-control", "role": "INTERACTION", "order": 1, "span": "NORMAL"},
        ], "reveal_order": [],
    })
    scene = registry.materialize_plan(plan)
    assert scene.version == "agentic-canvas-scene-v3"
    assert [placement.role for placement in scene.presentation.placements] == ["PRIMARY", "INTERACTION"]


def test_generated_image_verified_alt_reaches_same_tutor_semantic_projection() -> None:
    from services.studio.agent.orchestrator import HostedGeneratedImage, _generated_image_block
    from services.studio.agentic_canvas import GeneratedImagePlanV1, build_agentic_tutor_projection

    block = _generated_image_block(GeneratedImagePlanV1(
        meaning="A seedling shows two leaves above soil and roots below.", title="Seedling",
        text_equivalent="Two green leaves above the soil line; branching roots below it.",
    ), HostedGeneratedImage(temporary_handle="image-call-1", content=b"fixture"))
    projected = build_agentic_tutor_projection(objective="Identify seedling parts", subject_key="SCIENCE",
        scene_status="READY", blocks=[block.model_dump(mode="json")], actions=[])
    assert projected["blocks"][0]["text_equivalent"] == block.accessibility.text_equivalent
    assert "image-call-1" not in str(projected)
