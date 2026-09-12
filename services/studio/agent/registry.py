"""Run-local provenance guard for declarative Canvas blocks."""

from __future__ import annotations

from services.studio.agentic_canvas import AgenticCanvasBlockV1, AgenticCanvasPlanV1, AgenticCanvasScene, AgenticCanvasSceneV2, AgenticCanvasSceneV3, CanvasPresentationV1, CustomVisualBlockV1


class PlanCompositionInconsistencyError(ValueError):
    """A selected CREATE candidate was omitted from the final Agent plan."""

    code = "PLAN_COMPOSITION_INCONSISTENT"

    def __init__(self, current_custom_candidate_block_id: str) -> None:
        self.current_custom_candidate_block_id = current_custom_candidate_block_id
        super().__init__(
            f"{self.code}: final plan omitted current custom candidate "
            f"{current_custom_candidate_block_id!r}"
        )


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

    def materialize_plan(
        self,
        plan: AgenticCanvasPlanV1,
        *,
        current_custom_candidate_block_id: str | None = None,
    ) -> AgenticCanvasScene:
        """Resolve a plan only from tool-owned blocks and enforce CREATE coherence.

        A current candidate is set only by a successful CREATE tool call.  It is
        not injected into a plan: the Agent must explicitly reference its
        canonical ID, while later CREATE calls simply supersede earlier ones.
        """
        if current_custom_candidate_block_id is not None:
            candidate = self._blocks.get(current_custom_candidate_block_id)
            if not isinstance(candidate, CustomVisualBlockV1):
                raise ValueError("Canvas current custom candidate was not produced by a registered tool")
            if current_custom_candidate_block_id not in {placement.block_id for placement in plan.placements}:
                raise PlanCompositionInconsistencyError(current_custom_candidate_block_id)
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
