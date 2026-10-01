from __future__ import annotations

from services.studio.agent.tools import (
    compute_math,
    convert_units,
    create_2d_scene,
    create_diagram,
    create_math_board,
    create_math_input,
    create_text_interaction,
    tool_names,
)


def test_compute_math_preserves_exact_result_and_explanation() -> None:
    result = compute_math(left="3/4", right="1/8", operation="ADD", purpose="compare the fractions")

    assert result.exact_result == "7/8"
    assert result.explanation == "compare the fractions"


def test_compute_math_compares_decimal_inputs_as_exact_rationals() -> None:
    result = compute_math(left="0.6", right="0.45", operation="COMPARE", purpose="compare decimal locations")

    assert result.left_exact == "3/5"
    assert result.right_exact == "9/20"
    assert result.exact_result == ">"


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
        "refine_custom_visual",
        "compute_math",
        "convert_units",
        "create_math_board",
        "create_2d_scene",
        "create_diagram",
        "create_text_interaction",
        "create_math_input",
        "create_custom_visual",
        "search_reusable_visuals",
        "instantiate_reusable_visual",
        "image_generation",
        "code_interpreter",
    )


def test_math_board_uses_typed_axes_markers_and_expressions() -> None:
    block = create_math_board(
        block_id="decimal-line",
        meaning="Compare exact decimal positions.",
        label="Decimal comparison",
        board_kind="NUMBER_LINE",
        axes=[{"axis": "X", "minimum": "0", "maximum": "1", "step": "1/20"}],
        markers=[
            {"id": "decimal-a", "label": "0.45", "value": "9/20", "marker_kind": "POINT", "draggable": True},
            {"id": "decimal-b", "label": "0.6", "value": "3/5", "marker_kind": "POINT", "draggable": True},
        ],
        expressions=[
            {"id": "comparison", "label": "Comparison", "latex": r"0.45 < 0.6", "role": "DERIVED"}
        ],
    )

    assert block.axes[0].step == "1/20"
    assert [marker.value for marker in block.markers] == ["9/20", "3/5"]
    assert block.expressions[0].role == "DERIVED"
    assert [element.id for element in block.elements] == ["decimal-a", "decimal-b", "comparison"]
    assert block.axis_min == "0" and block.axis_max == "1"


def test_spatial_diagram_and_text_tools_store_meaningful_typed_structures() -> None:
    spatial = create_2d_scene(
        block_id="forces",
        meaning="Two forces act on the cart.",
        label="Force scene",
        objects=[
            {"id": "cart", "label": "Cart", "object_kind": "RECTANGLE", "position": {"x": "40", "y": "50"}, "draggable": False},
            {"id": "force", "label": "Applied force", "object_kind": "ARROW", "position": {"x": "65", "y": "50"}, "draggable": True},
        ],
        relations=[{"source_id": "force", "target_id": "cart", "relation": "ACTS_ON", "label": "acts on"}],
    )
    diagram = create_diagram(
        block_id="water-cycle",
        meaning="Water changes state in a repeating cycle.",
        label="Water cycle",
        topology="CYCLE",
        layout="RADIAL",
        nodes=[
            {"id": "evaporation", "label": "Evaporation", "node_kind": "PROCESS"},
            {"id": "condensation", "label": "Condensation", "node_kind": "PROCESS"},
        ],
        edges=[{"source_id": "evaporation", "target_id": "condensation", "relation": "NEXT", "label": "then"}],
    )
    text = create_text_interaction(
        block_id="sequence",
        meaning="Order the supplied stages.",
        label="Order stages",
        interaction_family="ORDERING",
        prompt="Place the stages in order.",
        items=[
            {"id": "stage-a", "text": "First supplied stage", "group_id": None},
            {"id": "stage-b", "text": "Second supplied stage", "group_id": None},
        ],
        groups=[],
        relations=[{"source_id": "stage-a", "target_id": "stage-b", "relation": "BEFORE"}],
    )

    assert spatial.relations[0].relation == "ACTS_ON"
    assert diagram.nodes[0].node_kind == "PROCESS"
    assert diagram.edges[0].source_id == "evaporation"
    assert text.items[1].text == "Second supplied stage"
    assert all(element.current_value is None for element in text.elements)
    assert text.allowed_actions == ["SELECT", "REORDER", "SUBMIT"]
    assert [element.id for element in spatial.elements] == ["cart", "force"]


def test_spatial_layout_rejects_collapsed_labels_without_rescaling_small_coordinates() -> None:
    import pytest

    def obj(identifier: str, x: str, y: str = "50") -> dict[str, object]:
        return {"id": identifier, "label": identifier[0], "object_kind": "CIRCLE", "position": {"x": x, "y": y}, "draggable": False}

    with pytest.raises(ValueError, match="0..100 logical units"):
        create_2d_scene(block_id="collapsed", meaning="Two states of one atom", label="Atom",
                        objects=[obj("first", "0.38"), obj("second", "0.62")])
    # A small coordinate is valid when its label remains distinct and visible.
    scene = create_2d_scene(block_id="small-valid", meaning="Two separate positions", label="Positions",
                            objects=[obj("first", "0.5"), obj("second", "50")])
    assert scene.objects[0].position.x == "0.5"


def test_spatial_relation_caption_must_clear_objects_and_viewport() -> None:
    import pytest

    objects = [
        {"id": "left", "label": "الموضع الأول", "object_kind": "CIRCLE", "position": {"x": "35", "y": "50"}, "draggable": False},
        {"id": "middle", "label": "الذرة", "object_kind": "CIRCLE", "position": {"x": "50", "y": "50"}, "draggable": False},
        {"id": "right", "label": "الموضع الثاني", "object_kind": "CIRCLE", "position": {"x": "65", "y": "50"}, "draggable": False},
    ]
    valid = create_2d_scene(block_id="atom", meaning="Vibration", label="Atom", objects=objects,
        relations=[{"source_id": "left", "target_id": "right", "relation": "MOVES_TOWARD", "label": "حركة ذهاب وإياب"}])
    assert valid.relations[0].label == "حركة ذهاب وإياب"
    with pytest.raises(ValueError, match="relation label clips"):
        create_2d_scene(block_id="top", meaning="Relation", label="Top", objects=[
            {"id": "one", "label": "One", "object_kind": "POINT", "position": {"x": "30", "y": "14"}, "draggable": False},
            {"id": "two", "label": "Two", "object_kind": "POINT", "position": {"x": "70", "y": "14"}, "draggable": False},
        ], relations=[{"source_id": "one", "target_id": "two", "relation": "NEAR", "label": "Near"}])


def test_typed_structures_reject_dangling_relations_and_capture_math_input_constraints() -> None:
    import pytest

    with pytest.raises(ValueError, match="known objects"):
        create_2d_scene(
            block_id="invalid-scene",
            meaning="Invalid relation.",
            label="Invalid",
            objects=[{"id": "known", "label": "Known", "object_kind": "POINT", "position": {"x": "0", "y": "0"}, "draggable": False}],
            relations=[{"source_id": "known", "target_id": "missing", "relation": "NEAR", "label": None}],
        )

    with pytest.raises(ValueError, match="known nodes"):
        create_diagram(
            block_id="invalid-diagram",
            meaning="Invalid edge.",
            label="Invalid",
            topology="FLOW",
            layout="AUTO",
            nodes=[{"id": "known", "label": "Known", "node_kind": "STATE"}],
            edges=[{"source_id": "known", "target_id": "missing", "relation": "NEXT", "label": None}],
        )

    math_input = create_math_input(
        block_id="equation-entry",
        meaning="Enter an equivalent equation.",
        label="Equation",
        prompt="Write an equivalent equation.",
        initial_value="",
        constraints=["Use one equality sign.", "Keep both sides equivalent."],
    )
    assert math_input.prompt == "Write an equivalent equation."
    assert math_input.constraints == ["Use one equality sign.", "Keep both sides equivalent."]
