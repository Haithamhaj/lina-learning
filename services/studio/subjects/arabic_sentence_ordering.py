"""Exact production contracts for one bounded Arabic sentence-ordering activity."""

from __future__ import annotations

from copy import deepcopy
from typing import Mapping

from services.studio.subjects.contracts import (
    AccessibilityContract, ActivityActionContract, ActivityContract, InteractionPolicy,
    PayloadValidatorContract, ReducerContract, ReducedMotionPolicy, RendererContract,
    SemanticValidationPolicy, SubjectCapabilityProfile, ValidationResult, ValidationStatus,
    ValidatorContract,
)


ARABIC_PROFILE_VERSION = "subject-profile-v2"
ACTIVITY_KEY = "arabic_sentence_ordering_workspace"
ACTIVITY_VERSION = "arabic-sentence-ordering-workspace-activity-v1"
RENDERER_KEY = "arabic-sentence-ordering-workspace"
RENDERER_VERSION = "arabic-sentence-ordering-workspace-renderer-v1"
SCENE_PAYLOAD_SCHEMA_VERSION = "arabic-sentence-ordering-workspace-scene-v1"
TOKEN_SCHEMA_VERSION = "arabic-sentence-ordering-token-v1"
REORDER_TOKEN_ACTION_KEY = "REORDER_TOKEN"
SUBMIT_CONFIGURATION_ACTION_KEY = "SUBMIT_CONFIGURATION"
REORDER_PAYLOAD_SCHEMA_VERSION = "arabic-sentence-ordering-workspace-reorder-v1"
SUBMIT_PAYLOAD_SCHEMA_VERSION = "arabic-sentence-ordering-workspace-submit-v1"
REORDER_EVENT_SCHEMA_VERSION = "arabic-sentence-ordering-workspace-event-v1"
SUBMIT_EVENT_SCHEMA_VERSION = "arabic-sentence-ordering-workspace-event-v1"
REORDER_EVENT_KIND = "arabic.sentence_ordering_workspace.token_reordered"
SUBMIT_EVENT_KIND = "arabic.sentence_ordering_workspace.configuration_submitted"
SUBMIT_INTERACTION_KIND = "ARABIC_SENTENCE_ORDERING_WORKSPACE_SUBMISSION"
REDUCER_KEY = "arabic-sentence-ordering-workspace-reducer"
REDUCER_VERSION = "arabic-sentence-ordering-workspace-reducer-v1"
SUBMIT_VALIDATOR_KEY = "arabic-sentence-ordering-workspace-submit-validator"
SUBMIT_VALIDATOR_VERSION = "arabic-sentence-ordering-workspace-submit-validator-v1"
FIXTURE_KEY = "arabic_sentence_ordering_fixture_orchid"
FIXTURE_VERSION = "arabic-sentence-ordering-fixture-orchid-v1"

# Opaque fixture identities do not encode token text, order, or grammatical role.
VERB_TOKEN_ID = "tok-6d3a"
STUDENT_TOKEN_ID = "tok-f18c"
LESSON_TOKEN_ID = "tok-2b7e"
_VALID_ORDER = (VERB_TOKEN_ID, STUDENT_TOKEN_ID, LESSON_TOKEN_ID)
# The instruction requires verb-first, not subject-before-object. Supplied case
# endings preserve the subject/object roles in the marked VOS alternative.
_VALID_ORDERS = frozenset((_VALID_ORDER, (VERB_TOKEN_ID, LESSON_TOKEN_ID, STUDENT_TOKEN_ID)))
_TOKEN_ID_SET = frozenset(_VALID_ORDER)
_INITIAL_TOKEN_ORDER = (STUDENT_TOKEN_ID, LESSON_TOKEN_ID, VERB_TOKEN_ID)
_TOKEN_CATALOG = (
    {"id": LESSON_TOKEN_ID, "text": "الدرسَ"},
    {"id": VERB_TOKEN_ID, "text": "تكتبُ"},
    {"id": STUDENT_TOKEN_ID, "text": "الطالبةُ"},
)

ACCESSIBILITY = AccessibilityContract(
    accessible_equivalent="Named move controls and a submit control perform every Arabic token reorder and submission.",
    keyboard_policy="Keyboard buttons perform the same typed reorder and submit operations as pointer interaction.",
    touch_policy="Pointer interaction supports touch drag/drop with the same semantic reorder operation.",
    direction_policy="Arabic academic tokens render RTL in their semantic reading order; outer Tutor locale never changes token identity.",
    mobile_fallback="Narrow layouts retain the RTL ordered tokens, named move controls, and submit control.",
    safe_fallback="When interaction is unavailable, the renderer presents ordered Arabic tokens and accessible move controls.",
    reduced_motion_policy=ReducedMotionPolicy.OPTIONAL_WITH_STATIC_EQUIVALENT,
)
ACCESSIBILITY_PAYLOAD = {
    "accessible_equivalent": "named-token-move-controls",
    "keyboard_policy": "equivalent-typed-operation",
    "touch_policy": "pointer-drag-equivalent",
    "direction_policy": "academic-rtl-with-locale-aware-outer-ui",
    "reduced_motion_policy": "static-feedback-equivalent",
}


def arabic_sentence_ordering_scene_seed() -> dict[str, object]:
    """Return browser-safe Arabic fixture data without a canonical-answer field."""

    return {
        "fixture_key": FIXTURE_KEY,
        "fixture_version": FIXTURE_VERSION,
        "token_schema_version": TOKEN_SCHEMA_VERSION,
        "tokens": deepcopy(list(_TOKEN_CATALOG)),
        "token_ids": list(_INITIAL_TOKEN_ORDER),
    }


def _require_exact_keys(payload: Mapping[str, object], expected: set[str], label: str) -> None:
    if set(payload) != expected:
        raise ValueError(f"{label} has an unsupported shape.")


def validate_token_catalog(value: object, *, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list of tokens.")
    tokens: list[dict[str, str]] = []
    for token in value:
        if not isinstance(token, Mapping) or set(token) != {"id", "text"}:
            raise ValueError(f"{label} token shape is unsupported.")
        token_id, text = token.get("id"), token.get("text")
        if not isinstance(token_id, str) or not token_id or not isinstance(text, str) or not text:
            raise ValueError(f"{label} token identity and visible text must be non-empty strings.")
        tokens.append({"id": token_id, "text": text})
    if len({token["id"] for token in tokens}) != len(tokens):
        raise ValueError(f"{label} token identities must be unique.")
    return tokens


def _token_ids(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(token_id, str) and token_id for token_id in value):
        raise ValueError(f"{label} must be a list of stable token identities.")
    if len(value) != len(_TOKEN_ID_SET) or set(value) != _TOKEN_ID_SET:
        raise ValueError(f"{label} must contain every known token exactly once.")
    return list(value)


def validate_scene_seed(payload: Mapping[str, object]) -> None:
    _require_exact_keys(payload, {"fixture_key", "fixture_version", "token_schema_version", "tokens", "token_ids"}, "Arabic sentence ordering scene seed")
    if payload.get("fixture_key") != FIXTURE_KEY or payload.get("fixture_version") != FIXTURE_VERSION:
        raise ValueError("Arabic sentence ordering scene seed does not identify the approved fixture.")
    if payload.get("token_schema_version") != TOKEN_SCHEMA_VERSION:
        raise ValueError("Arabic sentence ordering scene seed token schema is unsupported.")
    if validate_token_catalog(payload.get("tokens"), label="Arabic sentence ordering scene seed") != list(_TOKEN_CATALOG):
        raise ValueError("Arabic sentence ordering scene seed token catalog is unsupported.")
    if _token_ids(payload.get("token_ids"), label="Arabic sentence ordering scene tokens") != list(_INITIAL_TOKEN_ORDER):
        raise ValueError("Arabic sentence ordering scene seed order is unsupported.")


def validate_reorder_payload(payload: Mapping[str, object]) -> None:
    _require_exact_keys(payload, {"token_id", "from_index", "to_index"}, "Arabic sentence ordering reorder payload")
    token_id, from_index, to_index = payload.get("token_id"), payload.get("from_index"), payload.get("to_index")
    if not isinstance(token_id, str) or token_id not in _TOKEN_ID_SET or any(type(index) is not int or index < 0 or index >= len(_TOKEN_ID_SET) for index in (from_index, to_index)) or from_index == to_index:
        raise ValueError("Arabic sentence ordering reorder payload is unsupported.")


def validate_submit_payload(payload: Mapping[str, object]) -> None:
    _require_exact_keys(payload, {"token_ids"}, "Arabic sentence ordering submit payload")
    _token_ids(payload.get("token_ids"), label="Arabic sentence ordering submitted tokens")


def _state_token_ids(activity_state: Mapping[str, object]) -> list[str]:
    current = activity_state.get(ACTIVITY_KEY)
    if current is None:
        seed = activity_state.get("scene_seed")
        if not isinstance(seed, Mapping):
            raise ValueError("Arabic sentence ordering authoritative scene seed is unavailable.")
        validate_scene_seed(seed)
        return _token_ids(seed.get("token_ids"), label="Arabic sentence ordering scene tokens")
    if not isinstance(current, Mapping):
        raise ValueError("Arabic sentence ordering activity state is unsupported.")
    return _token_ids(current.get("token_ids"), label="Arabic sentence ordering activity tokens")


def validate_submit_configuration(payload: Mapping[str, object]) -> ValidationResult:
    action, activity_state = payload.get("action"), payload.get("activity_state")
    if not isinstance(action, Mapping) or not isinstance(activity_state, Mapping):
        raise ValueError("Arabic sentence ordering submit validation requires authoritative activity state.")
    validate_submit_payload(action)
    submitted = _token_ids(action.get("token_ids"), label="Arabic sentence ordering submitted tokens")
    if submitted != _state_token_ids(activity_state):
        return ValidationResult(ValidationStatus.INVALID, feedback_code="SUBMITTED_TOKEN_ORDER_DOES_NOT_MATCH_STATE", next_action_keys=(REORDER_TOKEN_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY))
    if tuple(submitted) in _VALID_ORDERS:
        return ValidationResult(ValidationStatus.VALID, feedback_code="ARABIC_VERB_INITIAL_SENTENCE_COMPLETE")
    return ValidationResult(ValidationStatus.INVALID, feedback_code="ARABIC_VERB_INITIAL_SENTENCE_NEEDS_REORDERING", next_action_keys=(REORDER_TOKEN_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY))


def reduce_arabic_sentence_ordering(snapshot: dict[str, object], event: object) -> dict[str, object]:
    sequence, actor, action_key, payload, event_id = (getattr(event, name, None) for name in ("sequence", "actor", "action_key", "payload", "id"))
    if not isinstance(sequence, int) or sequence <= int(snapshot["latest_event_sequence"]) or not isinstance(payload, Mapping):
        raise ValueError("Arabic sentence ordering event is unsupported.")
    next_snapshot = deepcopy(snapshot)
    next_snapshot["latest_event_sequence"] = sequence
    if actor == "STUDENT":
        next_snapshot["last_meaningful_student_event_id"] = event_id
    state_payload = dict(next_snapshot["state_payload"])
    token_ids = _state_token_ids(state_payload)
    if action_key == REORDER_TOKEN_ACTION_KEY:
        validate_reorder_payload(payload)
        token_id, from_index, to_index = payload["token_id"], payload["from_index"], payload["to_index"]
        if token_ids[from_index] != token_id:
            raise ValueError("Arabic sentence ordering source does not match authoritative state.")
        token_ids.pop(from_index)
        token_ids.insert(to_index, token_id)
    elif action_key == SUBMIT_CONFIGURATION_ACTION_KEY:
        validate_submit_payload(payload)
        if _token_ids(payload["token_ids"], label="Arabic sentence ordering submitted tokens") != token_ids:
            raise ValueError("Arabic sentence ordering submission does not match authoritative state.")
    else:
        raise ValueError("Arabic sentence ordering action is unsupported by its reducer.")
    activity_state: dict[str, object] = {"fixture_key": FIXTURE_KEY, "fixture_version": FIXTURE_VERSION, "token_schema_version": TOKEN_SCHEMA_VERSION, "token_ids": token_ids}
    if action_key == SUBMIT_CONFIGURATION_ACTION_KEY:
        activity_state["last_submission"] = {"token_ids": list(payload["token_ids"])}
    elif isinstance(state_payload.get(ACTIVITY_KEY), Mapping) and state_payload[ACTIVITY_KEY].get("last_submission") is not None:
        activity_state["last_submission"] = deepcopy(state_payload[ACTIVITY_KEY]["last_submission"])
    state_payload[ACTIVITY_KEY] = activity_state
    next_snapshot["state_payload"] = state_payload
    return next_snapshot


def make_arabic_sentence_ordering_profile() -> SubjectCapabilityProfile:
    reorder = ActivityActionContract(REORDER_TOKEN_ACTION_KEY, REORDER_EVENT_KIND, REORDER_EVENT_SCHEMA_VERSION, REORDER_PAYLOAD_SCHEMA_VERSION, "arabic-sentence-ordering-workspace-reorder-payload", InteractionPolicy.RECORD_ONLY, SemanticValidationPolicy.NONE)
    submit = ActivityActionContract(SUBMIT_CONFIGURATION_ACTION_KEY, SUBMIT_EVENT_KIND, SUBMIT_EVENT_SCHEMA_VERSION, SUBMIT_PAYLOAD_SCHEMA_VERSION, "arabic-sentence-ordering-workspace-submit-payload", InteractionPolicy.TUTOR_TRIGGERING, SemanticValidationPolicy.REQUIRED, SUBMIT_INTERACTION_KIND, SUBMIT_VALIDATOR_KEY, SUBMIT_VALIDATOR_VERSION)
    return SubjectCapabilityProfile(
        subject_key="ARABIC", profile_version=ARABIC_PROFILE_VERSION, supported_grade_scope=(), concept_namespace="lina.arabic.sentence-order",
        tutor_guidance_fragment="arabic-sentence-ordering-v1", grounding_policy_key="question-driven-grounding-v1", locale_policy_key="subject-independent-locale-v1", deterministic_fallback="safe-text-fallback-v1", canvas_specialist_profile_key=None,
        renderers=(RendererContract(RENDERER_KEY, RENDERER_VERSION, "ARABIC", (ACTIVITY_KEY,), SCENE_PAYLOAD_SCHEMA_VERSION, True, (REORDER_TOKEN_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY), (SUBMIT_VALIDATOR_KEY,), "arabic-sentence-ordering-workspace-state-v1", ACCESSIBILITY, False, False, True, "PRODUCTION"),),
        activities=(ActivityContract(ACTIVITY_KEY, ACTIVITY_VERSION, "ARABIC", "lina.arabic.sentence-order", RENDERER_KEY, RENDERER_VERSION, SCENE_PAYLOAD_SCHEMA_VERSION, "arabic-sentence-ordering-workspace-scene-payload", (reorder, submit), "A durable submitted token order validates the declared verb-initial Arabic sentence.", "Bounded validation feedback reflects durable state; it makes no broad claim about Arabic ability.", (), "Keep Tutor chat available and describe the declared Arabic tokens when the renderer is unavailable.", ACCESSIBILITY, REDUCER_KEY, REDUCER_VERSION, True),),
        validators=(ValidatorContract(SUBMIT_VALIDATOR_KEY, SUBMIT_VALIDATOR_VERSION, validate_submit_configuration, True),),
        payload_validators=(PayloadValidatorContract("arabic-sentence-ordering-workspace-scene-payload", SCENE_PAYLOAD_SCHEMA_VERSION, validate_scene_seed), PayloadValidatorContract("arabic-sentence-ordering-workspace-reorder-payload", REORDER_PAYLOAD_SCHEMA_VERSION, validate_reorder_payload), PayloadValidatorContract("arabic-sentence-ordering-workspace-submit-payload", SUBMIT_PAYLOAD_SCHEMA_VERSION, validate_submit_payload)),
        reducers=(ReducerContract(REDUCER_KEY, REDUCER_VERSION, reduce_arabic_sentence_ordering),),
    )
