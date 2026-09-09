"""Safe, declarative tools available to the single Canvas Agent.

These functions compose semantic blocks.  They never write Studio state, emit
renderer code, or receive student identities.
"""

from __future__ import annotations

import re
from decimal import Decimal
from functools import lru_cache

from pint import UnitRegistry
from pydantic import BaseModel, ConfigDict, Field
from sympy import sympify

from services.studio.agentic_canvas import AgenticCanvasBlockV1, AgenticCanvasElementV1


_SAFE_EXPRESSION = re.compile(r"^[0-9+*/().\s-]+$")
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


class UnitConversionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    value: str = Field(min_length=1, max_length=120)
    unit: str = Field(min_length=1, max_length=80)


def tool_names() -> tuple[str, ...]:
    """The allowlisted local tools; hosted tools are configured separately."""
    return _TOOL_NAMES


def compute_math(*, expression: str, purpose: str) -> ComputationResult:
    """Evaluate a bounded arithmetic expression exactly for a stated learning purpose."""
    if not _SAFE_EXPRESSION.fullmatch(expression) or len(expression) > 160:
        raise ValueError("expression must contain only bounded arithmetic notation")
    if not purpose.strip():
        raise ValueError("purpose is required")
    value = sympify(expression, evaluate=True)
    if getattr(value, "free_symbols", set()):
        raise ValueError("expression must be numeric")
    return ComputationResult(exact_result=str(value), explanation=purpose)


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


def _block(*, block_id: str, block_type: str, meaning: str, label: str, value: str | None = None) -> AgenticCanvasBlockV1:
    return AgenticCanvasBlockV1(
        block_id=block_id,
        type=block_type,
        meaning=meaning,
        elements=[AgenticCanvasElementV1(id=f"{block_id}-primary", label=label, current_value=value)],
    )


def create_math_board(*, block_id: str, meaning: str, label: str, expression: str) -> AgenticCanvasBlockV1:
    return _block(block_id=block_id, block_type="MATH_BOARD", meaning=meaning, label=label, value=expression)


def create_2d_scene(*, block_id: str, meaning: str, label: str) -> AgenticCanvasBlockV1:
    return _block(block_id=block_id, block_type="SCENE_2D", meaning=meaning, label=label)


def create_diagram(*, block_id: str, meaning: str, label: str) -> AgenticCanvasBlockV1:
    return _block(block_id=block_id, block_type="DIAGRAM", meaning=meaning, label=label)


def create_text_interaction(*, block_id: str, meaning: str, label: str, prompt: str) -> AgenticCanvasBlockV1:
    return _block(block_id=block_id, block_type="TEXT_INTERACTION", meaning=meaning, label=label, value=prompt)


def create_math_input(*, block_id: str, meaning: str, label: str, initial_value: str = "") -> AgenticCanvasBlockV1:
    return _block(block_id=block_id, block_type="MATH_INPUT", meaning=meaning, label=label, value=initial_value)
