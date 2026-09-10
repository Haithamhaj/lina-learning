"""Safe, declarative tools available to the single Canvas Agent.

These functions compose semantic blocks.  They never write Studio state, emit
renderer code, or receive student identities.
"""

from __future__ import annotations

import re
from decimal import Decimal
from functools import lru_cache
from fractions import Fraction
from typing import Literal

from pint import UnitRegistry
from pydantic import BaseModel, ConfigDict, Field
from sympy import Rational

from services.studio.agentic_canvas import AccessibilitySpecV1, AgenticCanvasBlockV1, AgenticCanvasElementV1, DiagramBlockV1, MathBoardBlockV1, MathInputBlockV1, Scene2DBlockV1, TextInteractionBlockV1


_TOOL_NAMES = (
    "compute_math",
    "convert_units",
    "create_math_board",
    "create_2d_scene",
    "create_diagram",
    "create_text_interaction",
    "create_math_input",
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
    """The allowlisted local tools; hosted tools are configured separately."""
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


def _common(*, block_id: str, block_type: str, meaning: str, label: str, value: str | None = None) -> dict[str, object]:
    return dict(
        block_id=block_id,
        type=block_type,
        meaning=meaning,
        title=label,
        accessibility=AccessibilitySpecV1(text_equivalent=meaning),
        elements=[AgenticCanvasElementV1(id=f"{block_id}-primary", label=label, current_value=value)],
    )


def create_math_board(*, block_id: str, meaning: str, label: str, expression: str) -> AgenticCanvasBlockV1:
    return MathBoardBlockV1(**_common(block_id=block_id, block_type="MATH_BOARD", meaning=meaning, label=label, value=expression), board_kind="NUMBER_LINE")


def create_2d_scene(*, block_id: str, meaning: str, label: str) -> AgenticCanvasBlockV1:
    return Scene2DBlockV1(**_common(block_id=block_id, block_type="SCENE_2D", meaning=meaning, label=label))


def create_diagram(*, block_id: str, meaning: str, label: str) -> AgenticCanvasBlockV1:
    return DiagramBlockV1(**_common(block_id=block_id, block_type="DIAGRAM", meaning=meaning, label=label), topology="CONCEPT_MAP")


def create_text_interaction(*, block_id: str, meaning: str, label: str, prompt: str) -> AgenticCanvasBlockV1:
    return TextInteractionBlockV1(**_common(block_id=block_id, block_type="TEXT_INTERACTION", meaning=meaning, label=label, value=prompt), interaction_family="ANNOTATION")


def create_math_input(*, block_id: str, meaning: str, label: str, initial_value: str = "") -> AgenticCanvasBlockV1:
    return MathInputBlockV1(**_common(block_id=block_id, block_type="MATH_INPUT", meaning=meaning, label=label, value=initial_value))
