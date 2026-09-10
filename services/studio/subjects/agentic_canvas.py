"""Exact Subject Registry and reducer contracts for Tutor-led Agentic Canvas."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from services.studio.agentic_canvas import AgenticCanvasActionV1, AgenticCanvasSceneV1
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
    SubjectCapabilityProfile,
    ValidationResult,
    ValidationStatus,
    ValidatorContract,
)


SUBJECT_KEY = "CANVAS"
PROFILE_VERSION = "agentic-canvas-profile-v1"
ACTIVITY_KEY = "agentic_canvas"
ACTIVITY_VERSION = "agentic-canvas-activity-v1"
RENDERER_KEY = "agentic-canvas"
RENDERER_VERSION = "agentic-canvas-renderer-v1"
SCENE_SCHEMA_VERSION = "agentic-canvas-scene-v1"
ACTION_SCHEMA_VERSION = "agentic-canvas-action-v1"
REDUCER_KEY = "agentic-canvas-reducer"
REDUCER_VERSION = "agentic-canvas-reducer-v1"
ACTION_VALIDATOR_KEY = "agentic-canvas-action-validator"
ACTION_VALIDATOR_VERSION = "agentic-canvas-action-validator-v1"
ACTIONS = ("FOCUS", "SELECT", "MOVE", "SET_VALUE", "CONNECT", "SUBMIT")
TUTOR_TRIGGERING_ACTIONS = frozenset({"SELECT", "MOVE", "SET_VALUE", "CONNECT", "SUBMIT"})


ACCESSIBILITY = AccessibilityContract(
    accessible_equivalent="Every Canvas block carries a concise text equivalent and named semantic elements.",
    keyboard_policy="Every enabled semantic action has an equivalent keyboard control.",
    touch_policy="Pointer and touch gestures settle to the same semantic operation.",
    direction_policy="Arabic prose may be RTL while mathematical notation remains LTR.",
    mobile_fallback="Typed blocks stack into readable named controls on narrow layouts.",
    safe_fallback="Tutor chat remains available when a Scene or visual capability cannot render.",
    reduced_motion_policy=ReducedMotionPolicy.OPTIONAL_WITH_STATIC_EQUIVALENT,
)


def validate_scene(payload: Mapping[str, object]) -> None:
    AgenticCanvasSceneV1.model_validate(dict(payload))


def validate_action_shape(payload: Mapping[str, object]) -> None:
    expected = {"version", "action", "block_id", "element_id", "from_value", "to_value"}
    if set(payload) != expected:
        raise ValueError("Agentic Canvas action has an unsupported shape.")
    AgenticCanvasActionV1.model_validate(dict(payload))


def validate_action_shape_for(payload: Mapping[str, object], action_key: str) -> None:
    validate_action_shape(payload)
    if payload.get("action") != action_key:
        raise ValueError("Agentic Canvas action payload does not match its registered action key.")


def _current_scene(activity_state: Mapping[str, object]) -> AgenticCanvasSceneV1:
    current = activity_state.get(ACTIVITY_KEY, activity_state.get("scene_seed"))
    if not isinstance(current, Mapping):
        raise ValueError("Agentic Canvas authoritative Scene is missing.")
    return AgenticCanvasSceneV1.model_validate(dict(current))


def validate_action(payload: Mapping[str, object]) -> ValidationResult:
    raw_action, activity_state = payload.get("action"), payload.get("activity_state")
    if not isinstance(raw_action, Mapping) or not isinstance(activity_state, Mapping):
        raise ValueError("Agentic Canvas authoritative state is required.")
    validate_action_shape(raw_action)
    action = AgenticCanvasActionV1.model_validate(dict(raw_action))
    scene = _current_scene(activity_state)
    block = next((item for item in scene.blocks if item.block_id == action.block_id), None)
    if block is None:
        raise ValueError("Agentic Canvas action references an unknown block.")
    if action.action not in block.allowed_actions:
        raise ValueError("Agentic Canvas action is not allowed by its block.")
    element = None
    if action.element_id is not None:
        element = next((item for item in block.elements if item.id == action.element_id), None)
        if element is None:
            raise ValueError("Agentic Canvas action references an unknown element.")
    if action.action in {"MOVE", "SET_VALUE", "CONNECT"}:
        if element is None or action.to_value is None:
            raise ValueError("Agentic Canvas mutation requires an element and semantic value.")
        if action.from_value != element.current_value:
            raise ValueError("Agentic Canvas mutation no longer matches authoritative state.")
    elif action.action in {"FOCUS", "SELECT"} and (action.from_value is not None or action.to_value is not None):
        raise ValueError("Agentic Canvas selection actions cannot mutate semantic values.")
    elif action.action == "SUBMIT" and action.to_value is not None:
        if element is None or action.from_value != element.current_value:
            raise ValueError("Agentic Canvas submission no longer matches authoritative state.")
    if action.action == "CONNECT" and not any(
        candidate.id == action.to_value for candidate_block in scene.blocks for candidate in candidate_block.elements
    ):
        raise ValueError("Agentic Canvas connection references an unknown semantic element.")
    return ValidationResult(ValidationStatus.VALID)


def reduce_agentic_canvas(snapshot: dict[str, object], event: object) -> dict[str, object]:
    if type(event.sequence) is not int or event.sequence <= snapshot["latest_event_sequence"]:
        raise ValueError("Agentic Canvas event sequence must advance.")
    state = snapshot.get("state_payload")
    if not isinstance(state, Mapping):
        raise ValueError("Agentic Canvas Snapshot state is missing.")
    validation = validate_action({"action": event.payload, "activity_state": state})
    if validation.status is not ValidationStatus.VALID:
        raise ValueError("Agentic Canvas action is invalid.")
    action = AgenticCanvasActionV1.model_validate(event.payload)
    current = _current_scene(state).model_dump(mode="json")
    if action.element_id is not None and action.to_value is not None:
        for block in current["blocks"]:
            if block["block_id"] != action.block_id:
                continue
            for element in block["elements"]:
                if element["id"] == action.element_id:
                    element["current_value"] = action.to_value
    AgenticCanvasSceneV1.model_validate(current)
    result = deepcopy(snapshot)
    result["latest_event_sequence"] = event.sequence
    if event.actor == "STUDENT":
        result["last_meaningful_student_event_id"] = event.id
    result["state_payload"][ACTIVITY_KEY] = current
    return result


def make_profile() -> SubjectCapabilityProfile:
    actions = tuple(
        ActivityActionContract(
            action_key=action,
            event_kind=f"canvas.agentic.{action.lower()}",
            event_schema_version="agentic-canvas-action-event-v1",
            payload_schema_version=ACTION_SCHEMA_VERSION,
            payload_validator_key=f"agentic-canvas-{action.lower()}-payload",
            interaction_policy=(
                InteractionPolicy.TUTOR_TRIGGERING
                if action in TUTOR_TRIGGERING_ACTIONS
                else InteractionPolicy.RECORD_ONLY
            ),
            semantic_validation_policy=SemanticValidationPolicy.REQUIRED,
            interaction_kind=(f"AGENTIC_CANVAS_{action}" if action in TUTOR_TRIGGERING_ACTIONS else None),
            validator_key=ACTION_VALIDATOR_KEY,
            validator_version=ACTION_VALIDATOR_VERSION,
        )
        for action in ACTIONS
    )
    return SubjectCapabilityProfile(
        subject_key=SUBJECT_KEY,
        profile_version=PROFILE_VERSION,
        supported_grade_scope=(),
        concept_namespace="lina.canvas.agentic",
        tutor_guidance_fragment="Canvas represents the Primary Tutor objective and never teaches independently.",
        grounding_policy_key="tutor-canvas-brief-v1",
        locale_policy_key="subject-independent-locale-v1",
        deterministic_fallback="tutor-chat-available-v1",
        canvas_specialist_profile_key="agentic-canvas-v1",
        activities=(ActivityContract(
            activity_key=ACTIVITY_KEY,
            activity_version=ACTIVITY_VERSION,
            subject_key=SUBJECT_KEY,
            concept_namespace="lina.canvas.agentic",
            renderer_key=RENDERER_KEY,
            renderer_version=RENDERER_VERSION,
            initial_scene_payload_schema_version=SCENE_SCHEMA_VERSION,
            initial_scene_payload_validator_key="agentic-canvas-scene-payload",
            actions=actions,
            completion_semantics="Only a Tutor-triggering semantic action requests continuation from the same Primary Tutor.",
            immediate_feedback_policy="Studio validates identity and state; Tutor owns explanation and grading.",
            support_action_keys=(),
            fallback="Tutor chat remains available.",
            accessibility=ACCESSIBILITY,
            reducer_key=REDUCER_KEY,
            reducer_version=REDUCER_VERSION,
            requires_explicit_hint=True,
        ),),
        renderers=(RendererContract(
            renderer_key=RENDERER_KEY,
            renderer_version=RENDERER_VERSION,
            subject_key=SUBJECT_KEY,
            supported_activity_keys=(ACTIVITY_KEY,),
            scene_input_schema_version=SCENE_SCHEMA_VERSION,
            interactive=True,
            supported_action_keys=ACTIONS,
            required_validator_keys=(ACTION_VALIDATOR_KEY,),
            state_adapter_key="agentic-canvas-state-v1",
            accessibility=ACCESSIBILITY,
            source_view_compatible=False,
            annotation_compatible=False,
            reconstruction_compatible=True,
            implementation_status="PRODUCTION",
        ),),
        validators=(ValidatorContract(
            validator_key=ACTION_VALIDATOR_KEY,
            validator_version=ACTION_VALIDATOR_VERSION,
            validator=validate_action,
            requires_activity_state=True,
        ),),
        payload_validators=(
            PayloadValidatorContract("agentic-canvas-scene-payload", SCENE_SCHEMA_VERSION, validate_scene),
            *(PayloadValidatorContract(
                f"agentic-canvas-{action.lower()}-payload",
                ACTION_SCHEMA_VERSION,
                lambda payload, key=action: validate_action_shape_for(payload, key),
            ) for action in ACTIONS),
        ),
        reducers=(ReducerContract(REDUCER_KEY, REDUCER_VERSION, reduce_agentic_canvas),),
    )
