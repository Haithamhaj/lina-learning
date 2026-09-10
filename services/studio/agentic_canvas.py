"""Declarative, renderer-free Agentic Canvas contracts and Tutor projection."""

from __future__ import annotations

from fractions import Fraction
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


_SEMANTIC_ID = r"^[a-z][a-z0-9_-]*$"
_EXACT_NUMBER = r"^[+-]?(?:\d+(?:\.\d+)?|\d+/\d+)$"


def _exact_fraction(value: str) -> Fraction:
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("Exact numeric values must be valid finite rationals") from exc


class MathAxisV1(BaseModel):
    """Exact mathematical axis semantics, independent of renderer geometry."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    axis: Literal["X", "Y"]
    minimum: str = Field(min_length=1, max_length=40, pattern=_EXACT_NUMBER)
    maximum: str = Field(min_length=1, max_length=40, pattern=_EXACT_NUMBER)
    step: str | None = Field(..., max_length=40, pattern=_EXACT_NUMBER)

    @model_validator(mode="after")
    def valid_range(self) -> "MathAxisV1":
        if _exact_fraction(self.minimum) >= _exact_fraction(self.maximum):
            raise ValueError("Math axis minimum must be less than maximum")
        if self.step is not None and _exact_fraction(self.step) <= 0:
            raise ValueError("Math axis step must be positive")
        return self


class MathMarkerV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=80, pattern=_EXACT_NUMBER)
    marker_kind: Literal["POINT", "OPEN_ENDPOINT", "CLOSED_ENDPOINT"]
    draggable: bool


class MathExpressionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    label: str = Field(min_length=1, max_length=120)
    latex: str = Field(min_length=1, max_length=300)
    role: Literal["GIVEN", "DERIVED", "TARGET"]


class LogicalPointV1(BaseModel):
    """Normalized logical coordinates; browser pixels never enter the Scene."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    x: str = Field(min_length=1, max_length=32, pattern=_EXACT_NUMBER)
    y: str = Field(min_length=1, max_length=32, pattern=_EXACT_NUMBER)

    @model_validator(mode="after")
    def normalized(self) -> "LogicalPointV1":
        values = (_exact_fraction(self.x), _exact_fraction(self.y))
        if any(value < 0 or value > 100 for value in values):
            raise ValueError("Logical coordinates must remain inside the 0..100 viewport")
        return self


class SpatialObjectV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    label: str = Field(min_length=1, max_length=120)
    object_kind: Literal["POINT", "CIRCLE", "RECTANGLE", "POLYGON", "ARROW", "LABEL"]
    position: LogicalPointV1
    draggable: bool


class SpatialRelationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    target_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    relation: Literal["NEAR", "ABOVE", "BELOW", "LEFT_OF", "RIGHT_OF", "CONTAINS", "CONNECTED_TO", "ACTS_ON", "MOVES_TOWARD", "PART_OF"]
    label: str | None = Field(..., max_length=120)


class DiagramNodeV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    label: str = Field(min_length=1, max_length=160)
    node_kind: Literal["CONCEPT", "STATE", "PROCESS", "ENTITY", "DECISION", "OUTCOME"]


class DiagramEdgeV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    target_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    relation: Literal["NEXT", "CAUSES", "RETURNS_TO", "PART_OF", "COMPARES", "RELATES_TO", "DEPENDS_ON"]
    label: str | None = Field(..., max_length=120)


class TextItemV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    text: str = Field(min_length=1, max_length=300)
    group_id: str | None = Field(..., max_length=64, pattern=_SEMANTIC_ID)


class TextGroupV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    label: str = Field(min_length=1, max_length=120)


class TextRelationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    target_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    relation: Literal["BEFORE", "MATCHES", "BELONGS_TO", "RELATES_TO"]


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
    axes: list[MathAxisV1] = Field(default_factory=list, max_length=2)
    markers: list[MathMarkerV1] = Field(default_factory=list, max_length=24)
    expressions: list[MathExpressionV1] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def unique_math_ids(self) -> "MathBoardBlockV1":
        ids = [item.id for item in [*self.markers, *self.expressions]]
        if len(ids) != len(set(ids)):
            raise ValueError("Math board semantic identifiers must be unique")
        if len({axis.axis for axis in self.axes}) != len(self.axes):
            raise ValueError("Math board axes must be unique")
        return self


class Scene2DBlockV1(AgenticCanvasBlockV1):
    type: Literal["SCENE_2D"]
    viewport_width_units: Literal[100] = 100
    viewport_height_units: Literal[100] = 100
    objects: list[SpatialObjectV1] = Field(default_factory=list, max_length=24)
    relations: list[SpatialRelationV1] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def valid_spatial_graph(self) -> "Scene2DBlockV1":
        ids = [item.id for item in self.objects]
        if len(ids) != len(set(ids)):
            raise ValueError("2D Scene object identifiers must be unique")
        known = set(ids)
        if any(edge.source_id not in known or edge.target_id not in known for edge in self.relations):
            raise ValueError("2D Scene relations must reference known objects")
        return self


class DiagramBlockV1(AgenticCanvasBlockV1):
    type: Literal["DIAGRAM"]
    topology: Literal["SEQUENCE", "CYCLE", "FLOW", "CAUSE_EFFECT", "COMPARISON", "HIERARCHY", "SYSTEM", "CONCEPT_MAP"]
    layout: Literal["HORIZONTAL", "VERTICAL", "RADIAL", "TREE", "GRID", "AUTO"] = "AUTO"
    nodes: list[DiagramNodeV1] = Field(default_factory=list, max_length=24)
    edges: list[DiagramEdgeV1] = Field(default_factory=list, max_length=36)

    @model_validator(mode="after")
    def valid_diagram_graph(self) -> "DiagramBlockV1":
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("Diagram node identifiers must be unique")
        known = set(ids)
        if any(edge.source_id not in known or edge.target_id not in known for edge in self.edges):
            raise ValueError("Diagram edges must reference known nodes")
        return self


class TextInteractionBlockV1(AgenticCanvasBlockV1):
    type: Literal["TEXT_INTERACTION"]
    interaction_family: Literal["ORDERING", "MATCHING", "CLASSIFICATION", "GROUPING", "HIGHLIGHT", "ANNOTATION", "RELATION", "TOKEN_MANIPULATION"]
    prompt: str = Field(default="Interact with the supplied text.", min_length=1, max_length=300)
    items: list[TextItemV1] = Field(default_factory=list, max_length=24)
    groups: list[TextGroupV1] = Field(default_factory=list, max_length=12)
    relations: list[TextRelationV1] = Field(default_factory=list, max_length=36)

    @model_validator(mode="after")
    def valid_text_graph(self) -> "TextInteractionBlockV1":
        item_ids = [item.id for item in self.items]
        group_ids = [group.id for group in self.groups]
        if len(item_ids) != len(set(item_ids)) or len(group_ids) != len(set(group_ids)):
            raise ValueError("Text interaction identifiers must be unique")
        if set(item_ids) & set(group_ids):
            raise ValueError("Text item and group identifiers must not overlap")
        known_items, known_groups = set(item_ids), set(group_ids)
        if any(item.group_id is not None and item.group_id not in known_groups for item in self.items):
            raise ValueError("Text items must reference known groups")
        known = known_items | known_groups
        if any(edge.source_id not in known or edge.target_id not in known for edge in self.relations):
            raise ValueError("Text relations must reference known items or groups")
        return self


class MathInputBlockV1(AgenticCanvasBlockV1):
    type: Literal["MATH_INPUT"]
    notation: Literal["LATEX"] = "LATEX"
    prompt: str = Field(default="Enter mathematical notation.", min_length=1, max_length=300)
    constraints: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(default_factory=list, max_length=8)


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
