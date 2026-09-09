from __future__ import annotations

from services.studio.agent.tools import (
    compute_math,
    convert_units,
    create_math_board,
    tool_names,
)


def test_compute_math_preserves_exact_result_and_explanation() -> None:
    result = compute_math(expression="(3/4) + (1/8)", purpose="compare the fractions")

    assert result.exact_result == "7/8"
    assert result.explanation == "compare the fractions"


def test_convert_units_returns_a_semantic_quantity_not_a_renderer_instruction() -> None:
    result = convert_units(value="2.5", from_unit="meter", to_unit="centimeter")

    assert result.value == "250"
    assert result.unit == "centimeter"
    assert "pixel" not in result.model_dump_json().lower()


def test_create_math_board_returns_a_declarative_agentic_canvas_block() -> None:
    block = create_math_board(
        block_id="fraction-model",
        meaning="Compare three quarters and one eighth as equal parts of a whole.",
        label="Fraction comparison",
        expression="3/4 + 1/8",
    )

    assert block.type == "MATH_BOARD"
    assert block.block_id == "fraction-model"
    assert block.elements[0].current_value == "3/4 + 1/8"


def test_registry_names_are_bounded_to_the_approved_canvas_tools() -> None:
    assert tool_names() == (
        "compute_math",
        "convert_units",
        "create_math_board",
        "create_2d_scene",
        "create_diagram",
        "create_text_interaction",
        "create_math_input",
    )
