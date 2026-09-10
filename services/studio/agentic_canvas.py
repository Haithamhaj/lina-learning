"""Declarative, renderer-free Agentic Canvas contracts and Tutor projection."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


AGENTIC_CANVAS_SCENE_VERSION = "agentic-canvas-scene-v1"
AGENTIC_CANVAS_ACTION_VERSION = "agentic-canvas-action-v1"
AGENTIC_CANVAS_PLAN_VERSION = "agentic-canvas-plan-v1"


class AgenticCanvasElementV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    label: str = Field(min_length=1, max_length=160)
    current_value: str | None = Field(..., max_length=240)


class AccessibilitySpecV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text_equivalent: str = Field(min_length=1, max_length=600)
    aria_label: str | None = Field(default=None, max_length=160)


class VisualStyleV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    color_role: Literal["PRIMARY", "SECONDARY", "ACCENT", "POSITIVE", "CAUTION", "MUTED", "NEUTRAL"] = "PRIMARY"
    emphasis: Literal["PRIMARY", "SUPPORT", "QUIET"] = "SUPPORT"
    surface: Literal["NONE", "CARD", "PANEL"] = "NONE"
    line_style: Literal["SOLID", "DASHED", "DOTTED"] | None = None


class ElementInteractionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selectable: bool = False
    draggable: bool = False
    connectable: bool = False
    editable: bool = False


class AgenticCanvasBlockV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    block_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    type: Literal["MATH_BOARD", "SCENE_2D", "DIAGRAM", "TEXT_INTERACTION", "MATH_INPUT", "IMAGE"]
    meaning: str = Field(min_length=1, max_length=500)
    title: str | None = Field(default=None, max_length=120)
    accessibility: AccessibilitySpecV1
    allowed_actions: list[Literal["FOCUS", "SELECT", "MOVE", "SET_VALUE", "CONNECT", "SUBMIT"]] = Field(default_factory=list, max_length=6)
    elements: list[AgenticCanvasElementV1] = Field(..., max_length=32)


class MathBoardBlockV1(AgenticCanvasBlockV1):
    type: Literal["MATH_BOARD"]
    board_kind: Literal["NUMBER_LINE", "CARTESIAN", "PLOT"]
    axis_min: str | None = Field(default=None, max_length=80)
    axis_max: str | None = Field(default=None, max_length=80)


class Scene2DBlockV1(AgenticCanvasBlockV1):
    type: Literal["SCENE_2D"]
    viewport_width_units: Literal[100] = 100
    viewport_height_units: Literal[100] = 100


class DiagramBlockV1(AgenticCanvasBlockV1):
    type: Literal["DIAGRAM"]
    topology: Literal["SEQUENCE", "CYCLE", "FLOW", "CAUSE_EFFECT", "COMPARISON", "HIERARCHY", "SYSTEM", "CONCEPT_MAP"]
    layout: Literal["HORIZONTAL", "VERTICAL", "RADIAL", "TREE", "GRID", "AUTO"] = "AUTO"


class TextInteractionBlockV1(AgenticCanvasBlockV1):
    type: Literal["TEXT_INTERACTION"]
    interaction_family: Literal["ORDERING", "MATCHING", "CLASSIFICATION", "GROUPING", "HIGHLIGHT", "ANNOTATION", "RELATION", "TOKEN_MANIPULATION"]


class MathInputBlockV1(AgenticCanvasBlockV1):
    type: Literal["MATH_INPUT"]
    notation: Literal["LATEX"] = "LATEX"


class ImageBlockV1(AgenticCanvasBlockV1):
    type: Literal["IMAGE"]
    studio_generated_asset_id: str = Field(min_length=1, max_length=64)


TypedAgenticCanvasBlockV1 = Annotated[Union[MathBoardBlockV1, Scene2DBlockV1, DiagramBlockV1, TextInteractionBlockV1, MathInputBlockV1, ImageBlockV1], Field(discriminator="type")]


class AgenticCanvasSceneV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[AGENTIC_CANVAS_SCENE_VERSION]
    objective: str = Field(min_length=1, max_length=500)
    subject_key: str = Field(min_length=1, max_length=64)
    blocks: list[TypedAgenticCanvasBlockV1] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def unique_block_ids(self) -> "AgenticCanvasSceneV1":
        if len({block.block_id for block in self.blocks}) != len(self.blocks):
            raise ValueError("Agentic Canvas block identifiers must be unique")
        return self


class AgenticCanvasPlanV1(BaseModel):
    """Agent final output references only run-local tool-produced blocks."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: Literal[AGENTIC_CANVAS_PLAN_VERSION]
    objective: str = Field(min_length=1, max_length=500)
    subject_key: str = Field(min_length=1, max_length=64)
    layout: Literal["FOCUS", "STACK", "SPLIT", "GRID", "FOCUS_SUPPORT", "OVERLAY"]
    palette: Literal["AUTO", "WARM", "COOL", "NATURE", "VIBRANT", "NEUTRAL"]
    motion: Literal["NONE", "SUBTLE", "REVEAL"]
    placements: list["CanvasBlockPlacementV1"] = Field(min_length=1, max_length=12)
    reveal_order: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def unique_block_ids(self) -> "AgenticCanvasPlanV1":
        block_ids = [placement.block_id for placement in self.placements]
        if len(set(block_ids)) != len(block_ids):
            raise ValueError("Agentic Canvas plan block identifiers must be unique")
        if self.reveal_order and (len(set(self.reveal_order)) != len(self.reveal_order) or set(self.reveal_order) - set(block_ids)):
            raise ValueError("Agentic Canvas reveal order must reference placed blocks exactly once")
        return self


class CanvasBlockPlacementV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    block_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    role: Literal["PRIMARY", "SUPPORT", "INTERACTION"]
    order: int = Field(ge=0, le=11)
    span: Literal["COMPACT", "NORMAL", "WIDE", "FULL"] = "NORMAL"


class AgenticCanvasActionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[AGENTIC_CANVAS_ACTION_VERSION]
    action: Literal["FOCUS", "SELECT", "MOVE", "SET_VALUE", "CONNECT", "SUBMIT"]
    block_id: str = Field(min_length=1, max_length=64)
    element_id: str | None = Field(default=None, min_length=1, max_length=64)
    from_value: str | None = Field(default=None, max_length=240)
    to_value: str | None = Field(default=None, max_length=240)


def build_agentic_tutor_projection(*, objective: str, subject_key: str, scene_status: str, blocks: list[dict[str, object]], actions: list[AgenticCanvasActionV1]) -> dict[str, object]:
    """Return only durable semantic state; browser/layout details never enter Tutor context."""
    parsed_blocks = [TypeAdapter(TypedAgenticCanvasBlockV1).validate_python(block) for block in blocks]
    return {
        "version": "agentic-canvas-tutor-projection-v1",
        "scene_objective": objective,
        "subject": subject_key,
        "scene_status": scene_status,
        "blocks": [
            {"block_id": block.block_id, "type": block.type, "meaning": block.meaning,
             "elements": [element.model_dump() for element in block.elements]}
            for block in parsed_blocks
        ],
        "current_focus": None,
        "recent_student_actions": [
            {"action": action.action, "block_id": action.block_id, "element_id": action.element_id,
             "from": action.from_value, "to": action.to_value}
            for action in actions
        ],
    }
