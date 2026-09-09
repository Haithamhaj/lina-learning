from copy import deepcopy

import pytest

from services.studio.canvas_specialist import (
    CANVAS_SPECIALIST_MATH_INPUT_PROPOSAL_SCHEMA_VERSION,
    CANVAS_SPECIALIST_MATH_VISUALIZATION_PROPOSAL_SCHEMA_VERSION,
    CANVAS_SPECIALIST_SPATIAL_PROPOSAL_SCHEMA_VERSION,
    MATH_INPUT_CAPABILITY_PACK_IDENTITY,
    MATH_VISUALIZATION_CAPABILITY_PACK_IDENTITY,
    SPATIAL_CAPABILITY_PACK_IDENTITY,
    proposal_contract,
    validate_proposal_against_frozen_pack,
)
from services.studio.subjects.canvas_production import (
    initial_activity_state,
    proposal_to_scene_contract,
    reduce_canvas_activity,
    validate_action,
)


CASES = (
    (
        SPATIAL_CAPABILITY_PACK_IDENTITY,
        CANVAS_SPECIALIST_SPATIAL_PROPOSAL_SCHEMA_VERSION,
        {
            "version": "canvas-specialist-spatial-proposal-v1", "pattern": "SPATIAL_MANIPULATION",
            "title": "Classify the fraction", "prompt": "Place three quarters inside less than one.",
            "objects": [{"semantic_key": "three-quarters", "label": "3/4", "support_ids": ["F1"]}],
            "targets": [{"semantic_key": "less-than-one", "label": "Less than 1", "relation": "INSIDE", "support_ids": ["F2", "R1"]}],
            "initial_placements": [{"object_semantic_key": "three-quarters", "target_semantic_key": None}],
            "interaction_affordances": ["PLACE_OBJECT"], "text_equivalent": "Three quarters is less than one.",
        },
        {"object_count_limit": [1, 1], "target_count_limit": [1, 1], "allowed_relations": ["INSIDE", "MATCH", "GROUP"], "allowed_interactions": ["PLACE_OBJECT"], "label_max_length": 40},
    ),
    (
        MATH_VISUALIZATION_CAPABILITY_PACK_IDENTITY,
        CANVAS_SPECIALIST_MATH_VISUALIZATION_PROPOSAL_SCHEMA_VERSION,
        {
            "version": "canvas-specialist-math-visualization-proposal-v1", "pattern": "MATH_VISUALIZATION",
            "title": "Plot point P", "prompt": "Place P at two, three.",
            "point": {"semantic_key": "point-p", "label": "P", "initial_x": 0, "initial_y": 0, "support_ids": ["F1"]},
            "target": {"x": 2, "y": 3, "support_ids": ["F2", "R1"]},
            "x_range": {"minimum": -10, "maximum": 10}, "y_range": {"minimum": -10, "maximum": 10},
            "interaction_affordances": ["PLACE_POINT", "SUBMIT_CONSTRUCTION"], "text_equivalent": "Point P belongs at (2, 3).",
        },
        {"construction_family": "CARTESIAN_POINT", "coordinate_bounds": [-10, 10], "point_count_limit": [1, 1], "allowed_interactions": ["PLACE_POINT", "SUBMIT_CONSTRUCTION"], "label_max_length": 24},
    ),
    (
        MATH_INPUT_CAPABILITY_PACK_IDENTITY,
        CANVAS_SPECIALIST_MATH_INPUT_PROPOSAL_SCHEMA_VERSION,
        {
            "version": "canvas-specialist-math-input-proposal-v1", "pattern": "MATH_INPUT",
            "title": "Add fractions", "prompt": "Write three quarters plus one quarter.",
            "initial_latex": "", "expected_form": "LATEX", "expression_max_length": 120,
            "support_ids": ["F1", "F2", "R1"], "interaction_affordances": ["SUBMIT_EXPRESSION"],
            "text_equivalent": "Enter the fraction addition expression and submit it.",
        },
        {"input_representation": "LATEX", "expression_max_length": 120, "allowed_interactions": ["SUBMIT_EXPRESSION"]},
    ),
)


def _pack(identity: str, pattern: str, capability: dict[str, object]) -> dict[str, object]:
    return {
        "version": "frozen-composition-pack-v3", "pattern": pattern, "topology": None,
        "capability_pack": {"identity": identity, **capability},
        "semantic_alignment": {
            "required_semantics": [{"id": "F1"}, {"id": "F2"}],
            "required_relations": [{"id": "R1"}], "must_not_imply": [],
        },
        "allowed_affordances": capability["allowed_interactions"],
    }


@pytest.mark.parametrize("identity,version,payload,capability", CASES)
def test_non_process_specialist_union_is_strict_semantic_and_maps_to_a_scene(identity, version, payload, capability):
    proposal = proposal_contract(identity, version).model_validate(payload)
    pack = _pack(identity, payload["pattern"], capability)
    validate_proposal_against_frozen_pack(proposal, pack)
    scene = proposal_to_scene_contract(proposal.model_dump(mode="json"), pack, locale="en", direction="ltr")
    assert scene["pattern"] == payload["pattern"]
    assert "renderer" not in scene and "engine" not in scene
    assert initial_activity_state(scene)["status"] == "IN_PROGRESS"


def test_non_process_proposals_reject_implementation_control_and_unknown_fields():
    identity, version, payload, _ = CASES[0]
    with pytest.raises(ValueError):
        proposal_contract(identity, version).model_validate({**payload, "renderer": "Konva"})
    with pytest.raises(ValueError):
        proposal_contract(identity, version).model_validate({**payload, "prompt": "Use Konva for this"})


def test_each_activity_reducer_returns_exact_semantic_state_without_browser_coordinates():
    for identity, version, payload, capability in CASES:
        pack = _pack(identity, payload["pattern"], capability)
        scene = proposal_to_scene_contract(payload, pack, locale="en", direction="ltr")
        state = initial_activity_state(scene)
        assert "pixel" not in repr(state).lower()
        assert callable(reduce_canvas_activity)


def test_math_visualization_schema_rejects_coordinates_outside_the_application_capability():
    identity, version, payload, _ = CASES[1]
    invalid = {**payload, "x_range": {"minimum": -11, "maximum": 10}}
    with pytest.raises(ValueError):
        proposal_contract(identity, version).model_validate(invalid)


def test_math_visualization_schema_requires_the_exact_application_plane():
    identity, version, payload, _ = CASES[1]
    invalid = {**payload, "x_range": {"minimum": -9, "maximum": 10}}
    with pytest.raises(ValueError):
        proposal_contract(identity, version).model_validate(invalid)


@pytest.mark.parametrize("x,y", [(-10, -10), (10, 10), (-3, 5)])
def test_math_visualization_accepts_each_integer_boundary_and_real_worksheet_point(x: int, y: int):
    identity, version, payload, _ = CASES[1]
    candidate = deepcopy(payload)
    candidate["target"] = {**candidate["target"], "x": x, "y": y}

    proposal = proposal_contract(identity, version).model_validate(candidate)

    assert (proposal.target.x, proposal.target.y) == (x, y)


@pytest.mark.parametrize("x,y", [(11, 0), (-11, 0), (1.5, 0)])
def test_math_visualization_rejects_out_of_range_or_non_integer_points(x: object, y: object):
    identity, version, payload, _ = CASES[1]
    candidate = deepcopy(payload)
    candidate["target"] = {**candidate["target"], "x": x, "y": y}

    with pytest.raises(ValueError):
        proposal_contract(identity, version).model_validate(candidate)


def test_math_visualization_specialist_schema_exposes_the_exact_ten_unit_bounds():
    identity, version, _, _ = CASES[1]

    schema = proposal_contract(identity, version).model_json_schema()

    for definition, fields in (("_ConstructionPoint", ("initial_x", "initial_y")), ("_TargetPoint", ("x", "y"))):
        for field in fields:
            assert schema["$defs"][definition]["properties"][field] == {
                "maximum": 10, "minimum": -10, "title": field.replace("_", " ").title(), "type": "integer",
            }


@pytest.mark.parametrize("action_key", ["PLACE_POINT", "SUBMIT_CONSTRUCTION"])
def test_math_visualization_actions_enforce_the_exact_ten_unit_plane(action_key: str):
    identity, _, payload, capability = CASES[1]
    scene = proposal_to_scene_contract(payload, _pack(identity, payload["pattern"], capability), locale="en", direction="ltr")
    activity_state = {"scene_seed": scene}

    for x, y in ((-10, -10), (10, 10), (-3, 5)):
        assert validate_action(
            {"action": {"point_id": "point-p", "x": x, "y": y}, "activity_state": activity_state},
            action_key,
        ).status.value == "VALID"
    for x, y in ((-11, 0), (11, 0), (0.5, 0)):
        with pytest.raises(ValueError):
            validate_action(
                {"action": {"point_id": "point-p", "x": x, "y": y}, "activity_state": activity_state},
                action_key,
            )
