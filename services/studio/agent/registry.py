"""Run-local provenance guard for declarative Canvas blocks."""

from __future__ import annotations

from services.studio.agentic_canvas import AgenticCanvasBlockV1, AgenticCanvasPlanV1, AgenticCanvasScene, AgenticCanvasSceneV2, AgenticCanvasSceneV3, CanvasPresentationV1, CustomVisualBlockV1


class CanvasBlockRegistry:
    """Retains only canonical blocks produced by an allowlisted tool in one run."""

    def __init__(self) -> None:
        self._blocks: dict[str, AgenticCanvasBlockV1] = {}

    def accept(self, block: AgenticCanvasBlockV1) -> AgenticCanvasBlockV1:
        existing = self._blocks.get(block.block_id)
        if existing is not None and existing != block:
            raise ValueError("Canvas tool block identifiers cannot be reused with different content")
        self._blocks[block.block_id] = block
        return block

    def validate_scene(self, scene: AgenticCanvasScene) -> None:
        for block in scene.blocks:
            accepted = self._blocks.get(block.block_id)
            if accepted is None or accepted != block:
                raise ValueError("Canvas scene block was not produced by a registered tool")

    def materialize_plan(self, plan: AgenticCanvasPlanV1) -> AgenticCanvasScene:
        blocks = []
        for placement in sorted(plan.placements, key=lambda item: item.order):
            block_id = placement.block_id
            block = self._blocks.get(block_id)
            if block is None:
                raise ValueError("Canvas plan block was not produced by a registered tool")
            blocks.append(block)
        scene_type = AgenticCanvasSceneV3 if any(isinstance(block, CustomVisualBlockV1) for block in blocks) else AgenticCanvasSceneV2
        return scene_type(
            version="agentic-canvas-scene-v3" if scene_type is AgenticCanvasSceneV3 else "agentic-canvas-scene-v2",
            objective=plan.objective,
            subject_key=plan.subject_key,
            presentation=CanvasPresentationV1(
                layout=plan.layout, palette=plan.palette, motion=plan.motion,
                placements=plan.placements, reveal_order=plan.reveal_order,
            ),
            blocks=blocks,
        )

    def blocks(self) -> tuple[AgenticCanvasBlockV1, ...]:
        return tuple(self._blocks.values())
