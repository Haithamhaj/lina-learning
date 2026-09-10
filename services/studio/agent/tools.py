"""Safe, declarative tools available to the single Canvas Agent.

These functions compose semantic blocks.  They never write Studio state, emit
renderer code, or receive student identities.
"""

from __future__ import annotations

import re
from decimal import Decimal
from functools import lru_cache
from fractions import Fraction
from typing import Literal, TypeVar

from pint import UnitRegistry
from pydantic import BaseModel, ConfigDict, Field
from sympy import Rational

from services.studio.agentic_canvas import (
    AccessibilitySpecV1,
    AgenticCanvasBlockV1,
    AgenticCanvasElementV1,
    DiagramBlockV1,
    DiagramEdgeV1,
    DiagramNodeV1,
    MathAxisV1,
    MathBoardBlockV1,
    MathExpressionV1,
    MathInputBlockV1,
    MathMarkerV1,
    Scene2DBlockV1,
    SpatialObjectV1,
    SpatialRelationV1,
    TextGroupV1,
    TextInteractionBlockV1,
    TextItemV1,
    TextRelationV1,
)


_TOOL_NAMES = (
    "compute_math",
    "convert_units",
    "create_math_board",
    "create_2d_scene",
    "create_diagram",
    "create_text_interaction",
    "create_math_input",
    "image_generation",
    "code_interpreter",
)


class ComputationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    exact_result: str = Field(min_length=1, max_length=240)
    explanation: str = Field(min_length=1, max_length=300)
    left_exact: str | None = Field(..., max_length=120)
    right_exact: str | None = Field(..., max_length=120)


class UnitConversionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    value: str = Field(min_length=1, max_length=120)
    unit: str = Field(min_length=1, max_length=80)


def tool_names() -> tuple[str, ...]:
    """The complete allowlisted local and hosted Canvas tool surface."""
    return _TOOL_NAMES


def _exact_rational(value: str) -> Rational:
    if len(value) > 80 or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d+)?|\d+/\d+)", value.strip()):
        raise ValueError("value must be a bounded decimal, integer, or fraction")
    fraction = Fraction(value)
    return Rational(fraction.numerator, fraction.denominator)


def compute_math(*, left: str, right: str, operation: Literal["ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "COMPARE"], purpose: str) -> ComputationResult:
    """Perform one typed exact rational operation for a stated learning purpose."""
    if not purpose.strip():
        raise ValueError("purpose is required")
    left_value, right_value = _exact_rational(left), _exact_rational(right)
    if operation == "ADD": result = left_value + right_value
    elif operation == "SUBTRACT": result = left_value - right_value
    elif operation == "MULTIPLY": result = left_value * right_value
    elif operation == "DIVIDE":
        if right_value == 0: raise ValueError("division by zero is not allowed")
        result = left_value / right_value
    else: result = ">" if left_value > right_value else "<" if left_value < right_value else "="
    return ComputationResult(exact_result=str(result), explanation=purpose, left_exact=str(left_value), right_exact=str(right_value))


@lru_cache(maxsize=1)
def _unit_registry() -> UnitRegistry:
    return UnitRegistry(autoconvert_offset_to_baseunit=True)


def convert_units(*, value: str, from_unit: str, to_unit: str) -> UnitConversionResult:
    """Convert a numeric quantity while preserving a semantic unit result."""
    if len(value) > 80 or len(from_unit) > 80 or len(to_unit) > 80:
        raise ValueError("quantity inputs are too long")
    # Pint owns dimensional arithmetic; Decimal avoids coercing a unit-bearing
    # Pint quantity through SymPy's dimensionless conversion path.
    quantity = Decimal(value) * _unit_registry()(from_unit)
    converted = quantity.to(to_unit)
    magnitude = converted.magnitude
    normalized = format(magnitude.normalize(), "f") if isinstance(magnitude, Decimal) else str(magnitude)
    return UnitConversionResult(value=normalized, unit=str(converted.units))


def _common(
    *,
    block_id: str,
    block_type: str,
    meaning: str,
    label: str,
    value: str | None = None,
    elements: list[AgenticCanvasElementV1] | None = None,
    allowed_actions: list[str] | None = None,
) -> dict[str, object]:
    return dict(
        block_id=block_id,
        type=block_type,
        meaning=meaning,
        title=label,
        accessibility=AccessibilitySpecV1(text_equivalent=meaning),
        elements=elements or [AgenticCanvasElementV1(id=f"{block_id}-primary", label=label, current_value=value)],
        allowed_actions=allowed_actions or [],
    )


_ModelT = TypeVar("_ModelT", bound=BaseModel)


def _parse_many(model: type[_ModelT], values: list[_ModelT | dict[str, object]] | None) -> list[_ModelT]:
    return [value if isinstance(value, model) else model.model_validate(value) for value in (values or [])]


def create_math_board(
    *,
    block_id: str,
    meaning: str,
    label: str,
    expression: str | None = None,
    board_kind: Literal["NUMBER_LINE", "CARTESIAN", "PLOT"] = "NUMBER_LINE",
    axes: list[MathAxisV1 | dict[str, object]] | None = None,
    markers: list[MathMarkerV1 | dict[str, object]] | None = None,
    expressions: list[MathExpressionV1 | dict[str, object]] | None = None,
) -> AgenticCanvasBlockV1:
    """Create exact axis, marker, and expression semantics for a math board."""

    parsed_axes = _parse_many(MathAxisV1, axes)
    parsed_markers = _parse_many(MathMarkerV1, markers)
    parsed_expressions = _parse_many(MathExpressionV1, expressions)
    if expression is not None and not parsed_expressions:
        parsed_expressions = [
            MathExpressionV1(
                id=f"{block_id}-expression",
                label=label,
                latex=expression,
                role="GIVEN",
            )
        ]
    elements = [
        AgenticCanvasElementV1(id=item.id, label=item.label, current_value=item.value)
        for item in parsed_markers
    ] + [
        AgenticCanvasElementV1(id=item.id, label=item.label, current_value=item.latex)
        for item in parsed_expressions
    ]
    x_axis = next((axis for axis in parsed_axes if axis.axis == "X"), None)
    return MathBoardBlockV1(
        **_common(
            block_id=block_id,
            block_type="MATH_BOARD",
            meaning=meaning,
            label=label,
            value=expression,
            elements=elements or None,
            allowed_actions=["SELECT", "MOVE"] if any(item.draggable for item in parsed_markers) else ["SELECT"],
        ),
        board_kind=board_kind,
        axis_min=None if x_axis is None else x_axis.minimum,
        axis_max=None if x_axis is None else x_axis.maximum,
        axes=parsed_axes,
        markers=parsed_markers,
        expressions=parsed_expressions,
    )


def create_2d_scene(
    *,
    block_id: str,
    meaning: str,
    label: str,
    objects: list[SpatialObjectV1 | dict[str, object]] | None = None,
    relations: list[SpatialRelationV1 | dict[str, object]] | None = None,
) -> AgenticCanvasBlockV1:
    """Create normalized logical objects and explicit spatial relations."""

    parsed_objects = _parse_many(SpatialObjectV1, objects)
    parsed_relations = _parse_many(SpatialRelationV1, relations)
    elements = [
        AgenticCanvasElementV1(id=item.id, label=item.label, current_value=f"{item.position.x},{item.position.y}")
        for item in parsed_objects
    ]
    return Scene2DBlockV1(
        **_common(
            block_id=block_id,
            block_type="SCENE_2D",
            meaning=meaning,
            label=label,
            elements=elements or None,
            allowed_actions=["SELECT", "MOVE"] if any(item.draggable for item in parsed_objects) else ["SELECT"],
        ),
        objects=parsed_objects,
        relations=parsed_relations,
    )


def create_diagram(
    *,
    block_id: str,
    meaning: str,
    label: str,
    topology: Literal["SEQUENCE", "CYCLE", "FLOW", "CAUSE_EFFECT", "COMPARISON", "HIERARCHY", "SYSTEM", "CONCEPT_MAP"] = "CONCEPT_MAP",
    layout: Literal["HORIZONTAL", "VERTICAL", "RADIAL", "TREE", "GRID", "AUTO"] = "AUTO",
    nodes: list[DiagramNodeV1 | dict[str, object]] | None = None,
    edges: list[DiagramEdgeV1 | dict[str, object]] | None = None,
) -> AgenticCanvasBlockV1:
    """Create stable nodes and explicit typed edges for a relationship diagram."""

    parsed_nodes = _parse_many(DiagramNodeV1, nodes)
    parsed_edges = _parse_many(DiagramEdgeV1, edges)
    elements = [
        AgenticCanvasElementV1(id=item.id, label=item.label, current_value=item.node_kind)
        for item in parsed_nodes
    ]
    return DiagramBlockV1(
        **_common(
            block_id=block_id,
            block_type="DIAGRAM",
            meaning=meaning,
            label=label,
            elements=elements or None,
            allowed_actions=["FOCUS", "SELECT"],
        ),
        topology=topology,
        layout=layout,
        nodes=parsed_nodes,
        edges=parsed_edges,
    )


def create_text_interaction(
    *,
    block_id: str,
    meaning: str,
    label: str,
    prompt: str,
    interaction_family: Literal["ORDERING", "MATCHING", "CLASSIFICATION", "GROUPING", "HIGHLIGHT", "ANNOTATION", "RELATION", "TOKEN_MANIPULATION"] = "ANNOTATION",
    items: list[TextItemV1 | dict[str, object]] | None = None,
    groups: list[TextGroupV1 | dict[str, object]] | None = None,
    relations: list[TextRelationV1 | dict[str, object]] | None = None,
) -> AgenticCanvasBlockV1:
    """Create supplied text items, grouping targets, and semantic relations."""

    parsed_items = _parse_many(TextItemV1, items)
    parsed_groups = _parse_many(TextGroupV1, groups)
    parsed_relations = _parse_many(TextRelationV1, relations)
    elements = [
        AgenticCanvasElementV1(id=item.id, label=item.text, current_value=item.group_id)
        for item in parsed_items
    ] + [
        AgenticCanvasElementV1(id=item.id, label=item.label, current_value=None)
        for item in parsed_groups
    ]
    return TextInteractionBlockV1(
        **_common(
            block_id=block_id,
            block_type="TEXT_INTERACTION",
            meaning=meaning,
            label=label,
            value=prompt,
            elements=elements or None,
            allowed_actions=["SELECT", "MOVE", "CONNECT", "SUBMIT"],
        ),
        interaction_family=interaction_family,
        prompt=prompt,
        items=parsed_items,
        groups=parsed_groups,
        relations=parsed_relations,
    )


def create_math_input(
    *,
    block_id: str,
    meaning: str,
    label: str,
    prompt: str = "Enter mathematical notation.",
    initial_value: str = "",
    constraints: list[str] | None = None,
) -> AgenticCanvasBlockV1:
    """Create one bounded notation input without embedding evaluation code."""

    return MathInputBlockV1(
        **_common(
            block_id=block_id,
            block_type="MATH_INPUT",
            meaning=meaning,
            label=label,
            value=initial_value,
            allowed_actions=["FOCUS", "SET_VALUE", "SUBMIT"],
        ),
        prompt=prompt,
        constraints=constraints or [],
    )
