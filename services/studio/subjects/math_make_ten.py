"""Exact production contracts for the bounded 9 + 6 -> 10 + 5 Make-Ten activity."""

from __future__ import annotations

from copy import deepcopy
from typing import Mapping

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


MATH_PROFILE_VERSION = "subject-profile-v2"
ACTIVITY_KEY = "ten_frame_group_transfer"
ACTIVITY_VERSION = "ten-frame-group-transfer-activity-v1"
RENDERER_KEY = "ten-frame-group-transfer"
RENDERER_VERSION = "ten-frame-group-transfer-renderer-v1"
SCENE_PAYLOAD_SCHEMA_VERSION = "ten-frame-group-transfer-scene-v1"
TRANSFER_ITEM_ACTION_KEY = "TRANSFER_ITEM"
SUBMIT_CONFIGURATION_ACTION_KEY = "SUBMIT_CONFIGURATION"
TRANSFER_PAYLOAD_SCHEMA_VERSION = "ten-frame-group-transfer-transfer-v1"
SUBMIT_PAYLOAD_SCHEMA_VERSION = "ten-frame-group-transfer-submit-v1"
TRANSFER_EVENT_SCHEMA_VERSION = "ten-frame-group-transfer-event-v1"
SUBMIT_EVENT_SCHEMA_VERSION = "ten-frame-group-transfer-event-v1"
TRANSFER_EVENT_KIND = "math.ten_frame_group_transfer.item_transferred"
SUBMIT_EVENT_KIND = "math.ten_frame_group_transfer.submitted"
SUBMIT_INTERACTION_KIND = "MATH_TEN_FRAME_GROUP_TRANSFER_SUBMISSION"
REDUCER_KEY = "ten-frame-group-transfer-reducer"
REDUCER_VERSION = "ten-frame-group-transfer-reducer-v1"
SUBMIT_VALIDATOR_KEY = "ten-frame-group-transfer-submit-validator"
SUBMIT_VALIDATOR_VERSION = "ten-frame-group-transfer-submit-validator-v1"

TEN_FRAME_GROUP_ID = "ten-frame"
ONES_GROUP_ID = "ones-group"
_TEN_FRAME_ITEM_IDS = tuple(f"ten-frame-{number:02d}" for number in range(1, 10))
_ONES_GROUP_ITEM_IDS = tuple(f"ones-group-{number:02d}" for number in range(1, 7))
_ALL_ITEM_IDS = _TEN_FRAME_ITEM_IDS + _ONES_GROUP_ITEM_IDS
_GROUP_IDS = (TEN_FRAME_GROUP_ID, ONES_GROUP_ID)

ACCESSIBILITY = AccessibilityContract(
    accessible_equivalent="Named move controls and a submit control perform every transfer and submission.",
    keyboard_policy="Keyboard buttons perform the same typed transfer and submit operations as pointer interaction.",
    touch_policy="Pointer interaction supports touch drag/drop with the same semantic transfer operation.",
    direction_policy="The renderer accepts English, Arabic, and mixed-direction scene presentation without changing item identity.",
    mobile_fallback="Narrow layouts retain named group controls and the complete item count.",
    safe_fallback="When interaction is unavailable, the renderer presents the two named groups and accessible move controls.",
    reduced_motion_policy=ReducedMotionPolicy.OPTIONAL_WITH_STATIC_EQUIVALENT,
)

ACCESSIBILITY_PAYLOAD = {
    "accessible_equivalent": "named-move-controls",
    "keyboard_policy": "equivalent-typed-operation",
    "touch_policy": "pointer-drag-equivalent",
    "direction_policy": "locale-and-direction-aware",
    "reduced_motion_policy": "static-feedback-equivalent",
}


def make_ten_scene_seed() -> dict[str, object]:
    """Return fresh immutable-by-convention seed data for this one known activity."""

    return {
        "scenario": "nine-plus-six-make-ten-v1",
        "items": [
            {"id": item_id, "initial_group_id": TEN_FRAME_GROUP_ID}
            for item_id in _TEN_FRAME_ITEM_IDS
        ]
        + [
            {"id": item_id, "initial_group_id": ONES_GROUP_ID}
            for item_id in _ONES_GROUP_ITEM_IDS
        ],
        "groups": {
            TEN_FRAME_GROUP_ID: {"id": TEN_FRAME_GROUP_ID, "item_ids": list(_TEN_FRAME_ITEM_IDS)},
            ONES_GROUP_ID: {"id": ONES_GROUP_ID, "item_ids": list(_ONES_GROUP_ITEM_IDS)},
        },
        "total_count": len(_ALL_ITEM_IDS),
    }


def _require_exact_keys(payload: Mapping[str, object], expected: set[str], label: str) -> None:
    if set(payload) != expected:
        raise ValueError(f"{label} has an unsupported shape.")


def _string_list(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{label} must be a list of bounded item identities.")
    return list(value)


def _seed_groups(seed: Mapping[str, object]) -> dict[str, list[str]]:
    _require_exact_keys(seed, {"scenario", "items", "groups", "total_count"}, "Make-Ten scene seed")
    if seed.get("scenario") != "nine-plus-six-make-ten-v1" or seed.get("total_count") != len(_ALL_ITEM_IDS):
        raise ValueError("Make-Ten scene seed does not identify the approved 9 + 6 flow.")
    items = seed.get("items")
    if not isinstance(items, list) or len(items) != len(_ALL_ITEM_IDS):
        raise ValueError("Make-Ten scene seed must declare every stable item identity.")
    expected_initial_groups = {
        **{item_id: TEN_FRAME_GROUP_ID for item_id in _TEN_FRAME_ITEM_IDS},
        **{item_id: ONES_GROUP_ID for item_id in _ONES_GROUP_ITEM_IDS},
    }
    observed_initial_groups: dict[str, str] = {}
    for item in items:
        if not isinstance(item, Mapping) or set(item) != {"id", "initial_group_id"}:
            raise ValueError("Make-Ten scene items have an unsupported shape.")
        item_id, initial_group_id = item.get("id"), item.get("initial_group_id")
        if not isinstance(item_id, str) or not isinstance(initial_group_id, str):
            raise ValueError("Make-Ten scene items require stable string identities.")
        observed_initial_groups[item_id] = initial_group_id
    if observed_initial_groups != expected_initial_groups:
        raise ValueError("Make-Ten scene item identities or origins are unsupported.")
    groups = seed.get("groups")
    if not isinstance(groups, Mapping) or set(groups) != set(_GROUP_IDS):
        raise ValueError("Make-Ten scene seed groups are unsupported.")
    resolved: dict[str, list[str]] = {}
    for group_id, expected_items in (
        (TEN_FRAME_GROUP_ID, list(_TEN_FRAME_ITEM_IDS)),
        (ONES_GROUP_ID, list(_ONES_GROUP_ITEM_IDS)),
    ):
        group = groups.get(group_id)
        if not isinstance(group, Mapping) or set(group) != {"id", "item_ids"} or group.get("id") != group_id:
            raise ValueError("Make-Ten scene group identity is unsupported.")
        item_ids = _string_list(group.get("item_ids"), label="Make-Ten scene group items")
        if item_ids != expected_items:
            raise ValueError("Make-Ten scene group membership is unsupported.")
        resolved[group_id] = item_ids
    return resolved


def validate_scene_seed(payload: Mapping[str, object]) -> None:
    _seed_groups(payload)


def validate_transfer_payload(payload: Mapping[str, object]) -> None:
    _require_exact_keys(payload, {"item_id", "from_group_id", "to_group_id"}, "Make-Ten transfer payload")
    item_id, from_group_id, to_group_id = payload.get("item_id"), payload.get("from_group_id"), payload.get("to_group_id")
    if item_id not in _ALL_ITEM_IDS:
        raise ValueError("Make-Ten transfer item identity is unsupported.")
    if from_group_id not in _GROUP_IDS or to_group_id not in _GROUP_IDS or from_group_id == to_group_id:
        raise ValueError("Make-Ten transfer group identity is unsupported.")


def validate_submit_payload(payload: Mapping[str, object]) -> None:
    _require_exact_keys(payload, {"ten_frame_item_ids", "ones_group_item_ids"}, "Make-Ten submit payload")
    ten_frame_item_ids = _string_list(payload.get("ten_frame_item_ids"), label="Make-Ten ten-frame items")
    ones_group_item_ids = _string_list(payload.get("ones_group_item_ids"), label="Make-Ten ones-group items")
    submitted = ten_frame_item_ids + ones_group_item_ids
    if len(submitted) != len(_ALL_ITEM_IDS) or set(submitted) != set(_ALL_ITEM_IDS):
        raise ValueError("Make-Ten submit payload must account for every stable item exactly once.")


def _groups_from_activity_state(activity_state: Mapping[str, object]) -> dict[str, list[str]]:
    current = activity_state.get(ACTIVITY_KEY)
    if current is None:
        seed = activity_state.get("scene_seed")
        if not isinstance(seed, Mapping):
            raise ValueError("Make-Ten authoritative scene seed is unavailable.")
        return _seed_groups(seed)
    if not isinstance(current, Mapping):
        raise ValueError("Make-Ten activity state is unsupported.")
    groups = current.get("groups")
    if not isinstance(groups, Mapping) or set(groups) != set(_GROUP_IDS):
        raise ValueError("Make-Ten activity groups are unsupported.")
    resolved: dict[str, list[str]] = {}
    for group_id in _GROUP_IDS:
        group = groups.get(group_id)
        if not isinstance(group, Mapping) or group.get("id") != group_id:
            raise ValueError("Make-Ten activity group identity is unsupported.")
        resolved[group_id] = _string_list(group.get("item_ids"), label="Make-Ten activity group items")
    all_items = resolved[TEN_FRAME_GROUP_ID] + resolved[ONES_GROUP_ID]
    if len(all_items) != len(_ALL_ITEM_IDS) or set(all_items) != set(_ALL_ITEM_IDS):
        raise ValueError("Make-Ten activity state must preserve all stable item identities.")
    return resolved


def validate_submit_configuration(payload: Mapping[str, object]) -> ValidationResult:
    """Compare a submitted semantic claim with the locked durable Snapshot, never browser state."""

    action = payload.get("action")
    activity_state = payload.get("activity_state")
    if not isinstance(action, Mapping) or not isinstance(activity_state, Mapping):
        raise ValueError("Make-Ten submit validation requires an authoritative activity-state context.")
    validate_submit_payload(action)
    groups = _groups_from_activity_state(activity_state)
    submitted_ten = _string_list(action.get("ten_frame_item_ids"), label="Make-Ten submitted ten-frame items")
    submitted_ones = _string_list(action.get("ones_group_item_ids"), label="Make-Ten submitted ones-group items")
    if set(submitted_ten) != set(groups[TEN_FRAME_GROUP_ID]) or set(submitted_ones) != set(groups[ONES_GROUP_ID]):
        return ValidationResult(
            ValidationStatus.INVALID,
            feedback_code="SUBMITTED_CONFIGURATION_DOES_NOT_MATCH_STATE",
            next_action_keys=(TRANSFER_ITEM_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY),
        )
    if len(groups[TEN_FRAME_GROUP_ID]) == 10 and len(groups[ONES_GROUP_ID]) == 5:
        return ValidationResult(ValidationStatus.VALID, feedback_code="MAKE_TEN_COMPLETE")
    if len(groups[TEN_FRAME_GROUP_ID]) == 9 and len(groups[ONES_GROUP_ID]) == 6:
        return ValidationResult(
            ValidationStatus.INCOMPLETE,
            feedback_code="MOVE_ONE_ITEM_TO_MAKE_TEN",
            next_action_keys=(TRANSFER_ITEM_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY),
        )
    return ValidationResult(
        ValidationStatus.INVALID,
        feedback_code="GROUPS_DO_NOT_SHOW_MAKE_TEN",
        next_action_keys=(TRANSFER_ITEM_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY),
    )


def reduce_make_ten(snapshot: dict[str, object], event: object) -> dict[str, object]:
    """Reduce only the registered Make-Ten semantic events; no arithmetic or renderer catalog leaks out."""

    sequence = getattr(event, "sequence", None)
    actor = getattr(event, "actor", None)
    action_key = getattr(event, "action_key", None)
    payload = getattr(event, "payload", None)
    event_id = getattr(event, "id", None)
    if not isinstance(sequence, int) or sequence <= int(snapshot["latest_event_sequence"]):
        raise ValueError("Make-Ten event sequence must advance the Snapshot.")
    if not isinstance(payload, Mapping):
        raise ValueError("Make-Ten event payload is unsupported.")
    next_snapshot = deepcopy(snapshot)
    next_snapshot["latest_event_sequence"] = sequence
    if actor == "STUDENT":
        next_snapshot["last_meaningful_student_event_id"] = event_id
    state_payload = dict(next_snapshot["state_payload"])
    groups = _groups_from_activity_state(state_payload)
    if action_key == TRANSFER_ITEM_ACTION_KEY:
        validate_transfer_payload(payload)
        item_id = payload["item_id"]
        from_group_id = payload["from_group_id"]
        to_group_id = payload["to_group_id"]
        if item_id not in groups[from_group_id]:
            raise ValueError("Make-Ten transfer source does not match authoritative state.")
        groups[from_group_id].remove(item_id)
        groups[to_group_id].append(item_id)
    elif action_key != SUBMIT_CONFIGURATION_ACTION_KEY:
        raise ValueError("Make-Ten action is unsupported by its reducer.")
    all_items = groups[TEN_FRAME_GROUP_ID] + groups[ONES_GROUP_ID]
    if len(all_items) != len(_ALL_ITEM_IDS) or set(all_items) != set(_ALL_ITEM_IDS):
        raise ValueError("Make-Ten transfer must conserve every stable item identity.")
    activity_state: dict[str, object] = {
        "groups": {
            TEN_FRAME_GROUP_ID: {"id": TEN_FRAME_GROUP_ID, "item_ids": groups[TEN_FRAME_GROUP_ID]},
            ONES_GROUP_ID: {"id": ONES_GROUP_ID, "item_ids": groups[ONES_GROUP_ID]},
        },
        "total_count": len(_ALL_ITEM_IDS),
    }
    if action_key == SUBMIT_CONFIGURATION_ACTION_KEY:
        activity_state["last_submission"] = {
            "ten_frame_item_ids": list(payload["ten_frame_item_ids"]),
            "ones_group_item_ids": list(payload["ones_group_item_ids"]),
        }
    state_payload[ACTIVITY_KEY] = activity_state
    next_snapshot["state_payload"] = state_payload
    return next_snapshot


def make_ten_profile() -> SubjectCapabilityProfile:
    """Return the exact MATH v2 profile while leaving historical v1 resolution intact."""

    transfer = ActivityActionContract(
        action_key=TRANSFER_ITEM_ACTION_KEY,
        event_kind=TRANSFER_EVENT_KIND,
        event_schema_version=TRANSFER_EVENT_SCHEMA_VERSION,
        payload_schema_version=TRANSFER_PAYLOAD_SCHEMA_VERSION,
        payload_validator_key="ten-frame-group-transfer-transfer-payload",
        interaction_policy=InteractionPolicy.RECORD_ONLY,
        semantic_validation_policy=SemanticValidationPolicy.NONE,
    )
    submit = ActivityActionContract(
        action_key=SUBMIT_CONFIGURATION_ACTION_KEY,
        event_kind=SUBMIT_EVENT_KIND,
        event_schema_version=SUBMIT_EVENT_SCHEMA_VERSION,
        payload_schema_version=SUBMIT_PAYLOAD_SCHEMA_VERSION,
        payload_validator_key="ten-frame-group-transfer-submit-payload",
        interaction_policy=InteractionPolicy.TUTOR_TRIGGERING,
        semantic_validation_policy=SemanticValidationPolicy.REQUIRED,
        interaction_kind=SUBMIT_INTERACTION_KIND,
        validator_key=SUBMIT_VALIDATOR_KEY,
        validator_version=SUBMIT_VALIDATOR_VERSION,
    )
    return SubjectCapabilityProfile(
        subject_key="MATH",
        profile_version=MATH_PROFILE_VERSION,
        supported_grade_scope=(),
        concept_namespace="lina.math.make_ten",
        tutor_guidance_fragment="make-ten-group-transfer-v1",
        grounding_policy_key="question-driven-grounding-v1",
        locale_policy_key="subject-independent-locale-v1",
        deterministic_fallback="safe-text-fallback-v1",
        canvas_specialist_profile_key=None,
        renderers=(
            RendererContract(
                renderer_key=RENDERER_KEY,
                renderer_version=RENDERER_VERSION,
                subject_key="MATH",
                supported_activity_keys=(ACTIVITY_KEY,),
                scene_input_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
                interactive=True,
                supported_action_keys=(TRANSFER_ITEM_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY),
                required_validator_keys=(SUBMIT_VALIDATOR_KEY,),
                state_adapter_key="ten-frame-group-transfer-state-v1",
                accessibility=ACCESSIBILITY,
                source_view_compatible=False,
                annotation_compatible=False,
                reconstruction_compatible=True,
                implementation_status="PRODUCTION",
            ),
        ),
        activities=(
            ActivityContract(
                activity_key=ACTIVITY_KEY,
                activity_version=ACTIVITY_VERSION,
                subject_key="MATH",
                concept_namespace="lina.math.make_ten",
                renderer_key=RENDERER_KEY,
                renderer_version=RENDERER_VERSION,
                initial_scene_payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
                initial_scene_payload_validator_key="ten-frame-group-transfer-scene-payload",
                actions=(transfer, submit),
                completion_semantics="A durable submitted configuration validates the authoritative 10 plus 5 state.",
                immediate_feedback_policy="Counts and bounded validation feedback reflect durable state; color is never the only signal.",
                support_action_keys=(),
                fallback="Keep Tutor chat available and describe the two named groups when the renderer is unavailable.",
                accessibility=ACCESSIBILITY,
                reducer_key=REDUCER_KEY,
                reducer_version=REDUCER_VERSION,
                requires_explicit_hint=True,
            ),
        ),
        validators=(
            ValidatorContract(
                validator_key=SUBMIT_VALIDATOR_KEY,
                validator_version=SUBMIT_VALIDATOR_VERSION,
                validator=validate_submit_configuration,
                requires_activity_state=True,
            ),
        ),
        payload_validators=(
            PayloadValidatorContract(
                payload_validator_key="ten-frame-group-transfer-scene-payload",
                payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
                validator=validate_scene_seed,
            ),
            PayloadValidatorContract(
                payload_validator_key="ten-frame-group-transfer-transfer-payload",
                payload_schema_version=TRANSFER_PAYLOAD_SCHEMA_VERSION,
                validator=validate_transfer_payload,
            ),
            PayloadValidatorContract(
                payload_validator_key="ten-frame-group-transfer-submit-payload",
                payload_schema_version=SUBMIT_PAYLOAD_SCHEMA_VERSION,
                validator=validate_submit_payload,
            ),
        ),
        reducers=(ReducerContract(REDUCER_KEY, REDUCER_VERSION, reduce_make_ten),),
    )
