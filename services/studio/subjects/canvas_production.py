"""Bounded production contracts for non-Process Canvas patterns."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace

from services.studio.canvas_specialist import (
    CanvasSpecialistMathInputProposal,
    CanvasSpecialistMathVisualizationProposal,
    CanvasSpecialistSpatialProposal,
    proposal_contract,
    validate_proposal_against_frozen_pack,
)
from services.studio.subjects.contracts import (
    AccessibilityContract,
    ActivityActionContract,
    ActivityContract,
    InteractionPolicy,
    PayloadValidatorContract,
    ReducerContract,
    ReducedMotionPolicy,
    RendererContract,
    SemanticValidationPolicy,
    ValidationResult,
    ValidationStatus,
    ValidatorContract,
)
from services.studio.subjects.decimal_place_value import make_profile as make_math_profile


PROFILE_VERSION = "canvas-production-profile-v1"
PATTERN_CONTRACTS = {
    "SPATIAL_MANIPULATION": {
        "activity_key": "canvas_spatial_manipulation",
        "activity_version": "canvas-spatial-activity-v1",
        "renderer_key": "canvas-spatial-placement",
        "renderer_version": "canvas-spatial-placement-renderer-v1",
        "seed_version": "canvas-spatial-scene-v1",
        "state_version": "canvas-spatial-state-v1",
        "actions": ("PLACE_OBJECT",),
    },
    "MATH_VISUALIZATION": {
        "activity_key": "canvas_math_visualization",
        "activity_version": "canvas-math-visualization-activity-v1",
        "renderer_key": "canvas-coordinate-construction",
        "renderer_version": "canvas-coordinate-construction-renderer-v1",
        "seed_version": "canvas-math-visualization-scene-v1",
        "state_version": "canvas-math-visualization-state-v1",
        "actions": ("PLACE_POINT", "SUBMIT_CONSTRUCTION"),
    },
    "MATH_INPUT": {
        "activity_key": "canvas_math_input",
        "activity_version": "canvas-math-input-activity-v1",
        "renderer_key": "canvas-math-expression-input",
        "renderer_version": "canvas-math-expression-input-renderer-v1",
        "seed_version": "canvas-math-input-scene-v1",
        "state_version": "canvas-math-input-state-v1",
        "actions": ("SUBMIT_EXPRESSION",),
    },
}


def contract_for_pattern(pattern: str) -> dict[str, object]:
    contract = PATTERN_CONTRACTS.get(pattern)
    if contract is None:
        raise ValueError("Unsupported production Canvas pattern.")
    return dict(contract)


def proposal_to_scene_contract(
    proposal_payload: Mapping[str, object],
    pack: Mapping[str, object],
    *,
    locale: str,
    direction: str,
) -> dict[str, object]:
    if locale not in ("en", "ar") or direction not in ("ltr", "rtl", "auto"):
        raise ValueError("Unsupported Canvas locale/direction.")
    capability = pack.get("capability_pack")
    if not isinstance(capability, Mapping):
        raise ValueError("Missing Canvas capability identity.")
    proposal = proposal_contract(str(capability.get("identity")), str(proposal_payload.get("version"))).model_validate(proposal_payload)
    validate_proposal_against_frozen_pack(proposal, dict(pack))
    common = {
        "pattern": proposal.pattern,
        "title": proposal.title,
        "prompt": proposal.prompt,
        "text_equivalent": proposal.text_equivalent,
        "locale": locale,
        "direction": direction,
    }
    if isinstance(proposal, CanvasSpecialistSpatialProposal):
        seed = {
            **common,
            "objects": [item.model_dump(mode="json", exclude={"support_ids"}) for item in proposal.objects],
            "targets": [item.model_dump(mode="json", exclude={"support_ids"}) for item in proposal.targets],
            "initial_placements": [item.model_dump(mode="json") for item in proposal.initial_placements],
        }
    elif isinstance(proposal, CanvasSpecialistMathVisualizationProposal):
        seed = {
            **common,
            "point": proposal.point.model_dump(mode="json", exclude={"support_ids"}),
            "target": proposal.target.model_dump(mode="json", exclude={"support_ids"}),
            "x_range": proposal.x_range.model_dump(mode="json"),
            "y_range": proposal.y_range.model_dump(mode="json"),
        }
    elif isinstance(proposal, CanvasSpecialistMathInputProposal):
        seed = {
            **common,
            "initial_latex": proposal.initial_latex,
            "expected_form": proposal.expected_form,
            "expression_max_length": proposal.expression_max_length,
        }
    else:
        raise ValueError("Unsupported non-Process Canvas proposal.")
    validate_seed(seed)
    return seed


def validate_seed(seed: Mapping[str, object]) -> None:
    expected_common = {"pattern", "title", "prompt", "text_equivalent", "locale", "direction"}
    pattern = seed.get("pattern")
    contract_for_pattern(str(pattern))
    if not all(isinstance(seed.get(key), str) and seed[key] for key in ("title", "prompt", "text_equivalent", "locale", "direction")):
        raise ValueError("Canvas Scene text and locale are required.")
    if pattern == "SPATIAL_MANIPULATION":
        if set(seed) != expected_common | {"objects", "targets", "initial_placements"}:
            raise ValueError("Spatial Scene shape is invalid.")
        objects, targets, placements = seed["objects"], seed["targets"], seed["initial_placements"]
        if not isinstance(objects, list) or len(objects) != 1 or not isinstance(targets, list) or len(targets) != 1 or not isinstance(placements, list):
            raise ValueError("Spatial Scene bounds are invalid.")
        object_ids = {item.get("semantic_key") for item in objects if isinstance(item, Mapping) and set(item) == {"semantic_key", "label"}}
        target_ids = {item.get("semantic_key") for item in targets if isinstance(item, Mapping) and set(item) == {"semantic_key", "label", "relation"} and item.get("relation") in {"INSIDE", "MATCH", "GROUP"}}
        if len(object_ids) != len(objects) or len(target_ids) != len(targets):
            raise ValueError("Spatial Scene identities are invalid.")
        if {item.get("object_semantic_key") for item in placements if isinstance(item, Mapping) and set(item) == {"object_semantic_key", "target_semantic_key"}} != object_ids:
            raise ValueError("Spatial initial placements are invalid.")
        if any(item.get("target_semantic_key") is not None and item.get("target_semantic_key") not in target_ids for item in placements):
            raise ValueError("Spatial initial target is invalid.")
    elif pattern == "MATH_VISUALIZATION":
        if set(seed) != expected_common | {"point", "target", "x_range", "y_range"}:
            raise ValueError("Math visualization Scene shape is invalid.")
        point, target, xr, yr = seed["point"], seed["target"], seed["x_range"], seed["y_range"]
        if not all(isinstance(item, Mapping) for item in (point, target, xr, yr)):
            raise ValueError("Math visualization objects are invalid.")
        if set(point) != {"semantic_key", "label", "initial_x", "initial_y"} or set(target) != {"x", "y"} or set(xr) != {"minimum", "maximum"} or set(yr) != {"minimum", "maximum"}:
            raise ValueError("Math visualization semantic shape is invalid.")
        for value in (point["initial_x"], point["initial_y"], target["x"], target["y"], xr["minimum"], xr["maximum"], yr["minimum"], yr["maximum"]):
            if type(value) is not int or not -10 <= value <= 10:
                raise ValueError("Coordinate must be an exact bounded integer.")
        if not xr["minimum"] < xr["maximum"] or not yr["minimum"] < yr["maximum"]:
            raise ValueError("Coordinate range must increase.")
        if (xr["minimum"], xr["maximum"], yr["minimum"], yr["maximum"]) != (-4, 4, -4, 4):
            raise ValueError("The coordinate Scene must match the application plane.")
    else:
        if set(seed) != expected_common | {"initial_latex", "expected_form", "expression_max_length"}:
            raise ValueError("Math input Scene shape is invalid.")
        if seed["expected_form"] != "LATEX" or type(seed["expression_max_length"]) is not int or not 1 <= seed["expression_max_length"] <= 120 or not isinstance(seed["initial_latex"], str) or len(seed["initial_latex"]) > seed["expression_max_length"]:
            raise ValueError("Math input contract is invalid.")


def initial_activity_state(seed: Mapping[str, object]) -> dict[str, object]:
    validate_seed(seed)
    if seed["pattern"] == "SPATIAL_MANIPULATION":
        state = {"placements": {item["object_semantic_key"]: item["target_semantic_key"] for item in seed["initial_placements"]}}
    elif seed["pattern"] == "MATH_VISUALIZATION":
        state = {"point": {"x": seed["point"]["initial_x"], "y": seed["point"]["initial_y"]}, "submitted": None}
    else:
        state = {"submitted": None}
    return {"status": "IN_PROGRESS", **state}


def validate_action_shape(payload: Mapping[str, object], action_key: str) -> None:
    shapes = {
        "PLACE_OBJECT": {"object_id", "target_id"},
        "PLACE_POINT": {"point_id", "x", "y"},
        "SUBMIT_CONSTRUCTION": {"point_id", "x", "y"},
        "SUBMIT_EXPRESSION": {"format", "value"},
    }
    if action_key not in shapes or set(payload) != shapes[action_key]:
        raise ValueError("Canvas operation shape is invalid.")
    if action_key == "PLACE_OBJECT":
        if not all(isinstance(payload[key], str) and payload[key] for key in ("object_id", "target_id")):
            raise ValueError("Spatial operation requires semantic IDs.")
    elif action_key in {"PLACE_POINT", "SUBMIT_CONSTRUCTION"}:
        if not isinstance(payload["point_id"], str) or type(payload["x"]) is not int or type(payload["y"]) is not int:
            raise ValueError("Construction operation requires exact integers.")
    elif payload["format"] != "latex" or not isinstance(payload["value"], str):
        raise ValueError("Math input submission must be LaTeX.")


def validate_action(payload: Mapping[str, object], action_key: str) -> ValidationResult:
    action, activity_state = payload.get("action"), payload.get("activity_state")
    if not isinstance(action, Mapping) or not isinstance(activity_state, Mapping):
        raise ValueError("Authoritative Canvas state is required.")
    validate_action_shape(action, action_key)
    seed = activity_state.get("scene_seed")
    if not isinstance(seed, Mapping):
        raise ValueError("Canvas Scene seed is required.")
    validate_seed(seed)
    pattern = seed["pattern"]
    if action_key == "PLACE_OBJECT":
        if pattern != "SPATIAL_MANIPULATION" or action["object_id"] not in {item["semantic_key"] for item in seed["objects"]} or action["target_id"] not in {item["semantic_key"] for item in seed["targets"]}:
            raise ValueError("Spatial operation references unknown semantics.")
    elif action_key in {"PLACE_POINT", "SUBMIT_CONSTRUCTION"}:
        if pattern != "MATH_VISUALIZATION" or action["point_id"] != seed["point"]["semantic_key"] or not seed["x_range"]["minimum"] <= action["x"] <= seed["x_range"]["maximum"] or not seed["y_range"]["minimum"] <= action["y"] <= seed["y_range"]["maximum"]:
            raise ValueError("Construction is outside the semantic Scene.")
    elif pattern != "MATH_INPUT" or len(action["value"]) > seed["expression_max_length"]:
        raise ValueError("Expression exceeds the semantic Scene.")
    return ValidationResult(ValidationStatus.VALID)


def reduce_canvas_activity(snapshot: dict[str, object], event: object) -> dict[str, object]:
    if type(event.sequence) is not int or event.sequence <= snapshot["latest_event_sequence"]:
        raise ValueError("Event sequence must advance.")
    state = snapshot["state_payload"]
    seed = state.get("scene_seed")
    if not isinstance(seed, Mapping):
        raise ValueError("Canvas Scene seed is missing.")
    contract = contract_for_pattern(str(seed.get("pattern")))
    activity_key = str(contract["activity_key"])
    current = deepcopy(state.get(activity_key, initial_activity_state(seed)))
    validate_action({"action": event.payload, "activity_state": state}, event.action_key)
    if event.action_key == "PLACE_OBJECT":
        current["placements"][event.payload["object_id"]] = event.payload["target_id"]
    elif event.action_key == "PLACE_POINT":
        current["point"] = {"x": event.payload["x"], "y": event.payload["y"]}
    elif event.action_key == "SUBMIT_CONSTRUCTION":
        if current["point"] != {"x": event.payload["x"], "y": event.payload["y"]}:
            raise ValueError("Submitted construction differs from Snapshot.")
        current["submitted"] = deepcopy(dict(event.payload))
        current["status"] = "SUBMITTED"
    else:
        current["submitted"] = deepcopy(dict(event.payload))
        current["status"] = "SUBMITTED"
    result = deepcopy(snapshot)
    result["latest_event_sequence"] = event.sequence
    if event.actor == "STUDENT":
        result["last_meaningful_student_event_id"] = event.id
    result["state_payload"][activity_key] = current
    return result


ACCESSIBILITY = AccessibilityContract(
    "All visual meaning has concise labels and a live semantic state.",
    "Every operation has an exact keyboard control.",
    "Pointer and touch gestures settle to the same semantic operation.",
    "Arabic prose may be RTL; mathematical axes and expressions remain LTR.",
    "Controls remain usable on a narrow layout.",
    "Tutor chat remains available and the Workspace can reload server state.",
    ReducedMotionPolicy.OPTIONAL_WITH_STATIC_EQUIVALENT,
)


def make_profile():
    base = make_math_profile()
    activities = []
    renderers = []
    payload_validators = []
    reducers = []
    validators = []
    for pattern, contract in PATTERN_CONTRACTS.items():
        actions = []
        for action_key in contract["actions"]:
            action_slug = action_key.lower().replace("_", "-")
            tutor_triggering = action_key in {"PLACE_OBJECT", "SUBMIT_CONSTRUCTION", "SUBMIT_EXPRESSION"}
            action = ActivityActionContract(
                action_key=action_key,
                event_kind=f"canvas.{pattern.lower()}.{action_slug}",
                event_schema_version=f"canvas-{action_slug}-event-v1",
                payload_schema_version=f"canvas-{action_slug}-payload-v1",
                payload_validator_key=f"canvas-{action_slug}-payload",
                interaction_policy=InteractionPolicy.TUTOR_TRIGGERING if tutor_triggering else InteractionPolicy.RECORD_ONLY,
                semantic_validation_policy=SemanticValidationPolicy.REQUIRED,
                interaction_kind=f"CANVAS_{pattern}_{action_key}" if tutor_triggering else None,
                validator_key=f"canvas-{action_slug}",
                validator_version=f"canvas-{action_slug}-validator-v1",
            )
            actions.append(action)
            payload_validators.append(PayloadValidatorContract(action.payload_validator_key, action.payload_schema_version, lambda payload, key=action_key: validate_action_shape(payload, key)))
            validators.append(ValidatorContract(action.validator_key, action.validator_version, lambda payload, key=action_key: validate_action(payload, key), True))
        activity = ActivityContract(
            str(contract["activity_key"]), str(contract["activity_version"]), "MATH", "lina.canvas",
            str(contract["renderer_key"]), str(contract["renderer_version"]), str(contract["seed_version"]),
            f"{contract['activity_key']}-seed", tuple(actions),
            "Only a contract-declared meaningful placement or explicit submission starts Tutor continuation.",
            "Server validates semantic identity and bounds; Tutor owns explanation and grading.", (),
            "Tutor chat remains available.", ACCESSIBILITY, f"{contract['activity_key']}-reducer", "v1", True,
        )
        activities.append(activity)
        renderers.append(RendererContract(
            str(contract["renderer_key"]), str(contract["renderer_version"]), "MATH", (str(contract["activity_key"]),),
            str(contract["seed_version"]), True, tuple(contract["actions"]), tuple(action.validator_key for action in actions),
            str(contract["state_version"]), ACCESSIBILITY, False, False, False, "PRODUCTION",
        ))
        payload_validators.append(PayloadValidatorContract(f"{contract['activity_key']}-seed", str(contract["seed_version"]), validate_seed))
        reducers.append(ReducerContract(f"{contract['activity_key']}-reducer", "v1", reduce_canvas_activity))
    return replace(
        base,
        profile_version=PROFILE_VERSION,
        concept_namespace="lina.canvas",
        canvas_specialist_profile_key="canvas-production-specialist-v1",
        activities=tuple(activities),
        renderers=tuple(renderers),
        validators=tuple(validators),
        payload_validators=tuple(payload_validators),
        reducers=tuple(reducers),
    )
