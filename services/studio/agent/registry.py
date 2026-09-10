"""Run-local provenance guard for declarative Canvas blocks."""

from __future__ import annotations

from services.studio.agentic_canvas import AgenticCanvasBlockV1, AgenticCanvasPlanV1, AgenticCanvasSceneV1


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

    def validate_scene(self, scene: AgenticCanvasSceneV1) -> None:
        for block in scene.blocks:
            accepted = self._blocks.get(block.block_id)
            if accepted is None or accepted != block:
                raise ValueError("Canvas scene block was not produced by a registered tool")

    def materialize_plan(self, plan: AgenticCanvasPlanV1) -> AgenticCanvasSceneV1:
        blocks = []
        for placement in sorted(plan.placements, key=lambda item: item.order):
            block_id = placement.block_id
            block = self._blocks.get(block_id)
            if block is None:
                raise ValueError("Canvas plan block was not produced by a registered tool")
            blocks.append(block)
        return AgenticCanvasSceneV1(
            version="agentic-canvas-scene-v1",
            objective=plan.objective,
            subject_key=plan.subject_key,
            blocks=blocks,
        )

    def blocks(self) -> tuple[AgenticCanvasBlockV1, ...]:
        return tuple(self._blocks.values())
