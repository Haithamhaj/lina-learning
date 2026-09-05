"""Exact production contracts for the bounded English sentence-ordering activity."""

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


ENGLISH_PROFILE_VERSION = "subject-profile-v2"
ACTIVITY_KEY = "sentence_ordering_workspace"
ACTIVITY_VERSION = "sentence-ordering-workspace-activity-v1"
RENDERER_KEY = "sentence-ordering-workspace"
RENDERER_VERSION = "sentence-ordering-workspace-renderer-v1"
SCENE_PAYLOAD_SCHEMA_VERSION = "sentence-ordering-workspace-scene-v1"
TOKEN_SCHEMA_VERSION = "sentence-ordering-token-v1"
REORDER_TOKEN_ACTION_KEY = "REORDER_TOKEN"
SUBMIT_CONFIGURATION_ACTION_KEY = "SUBMIT_CONFIGURATION"
REORDER_PAYLOAD_SCHEMA_VERSION = "sentence-ordering-workspace-reorder-v1"
SUBMIT_PAYLOAD_SCHEMA_VERSION = "sentence-ordering-workspace-submit-v1"
REORDER_EVENT_SCHEMA_VERSION = "sentence-ordering-workspace-event-v1"
SUBMIT_EVENT_SCHEMA_VERSION = "sentence-ordering-workspace-event-v1"
REORDER_EVENT_KIND = "english.sentence_ordering_workspace.token_reordered"
SUBMIT_EVENT_KIND = "english.sentence_ordering_workspace.configuration_submitted"
SUBMIT_INTERACTION_KIND = "ENGLISH_SENTENCE_ORDERING_WORKSPACE_SUBMISSION"
REDUCER_KEY = "sentence-ordering-workspace-reducer"
REDUCER_VERSION = "sentence-ordering-workspace-reducer-v1"
SUBMIT_VALIDATOR_KEY = "sentence-ordering-workspace-submit-validator"
SUBMIT_VALIDATOR_VERSION = "sentence-ordering-workspace-submit-validator-v1"
FIXTURE_KEY = "english_sentence_ordering_fixture_slate"
FIXTURE_VERSION = "english-sentence-ordering-fixture-slate-v1"

# These identifiers are fixture-owned opaque identities. They intentionally do
# not encode word text, canonical answer position, or serialisation order.
BIRDS_TOKEN_ID = "tok-c820"
FLY_TOKEN_ID = "tok-43bd"
OVER_TOKEN_ID = "tok-7f2c"
CLOUDS_TOKEN_ID = "tok-a91e"
_VALID_ORDER = (BIRDS_TOKEN_ID, FLY_TOKEN_ID, OVER_TOKEN_ID, CLOUDS_TOKEN_ID)
_TOKEN_ID_SET = frozenset(_VALID_ORDER)
_INITIAL_TOKEN_ORDER = (CLOUDS_TOKEN_ID, BIRDS_TOKEN_ID, OVER_TOKEN_ID, FLY_TOKEN_ID)
_TOKEN_CATALOG = (
    {"id": OVER_TOKEN_ID, "text": "over"},
    {"id": CLOUDS_TOKEN_ID, "text": "clouds"},
    {"id": FLY_TOKEN_ID, "text": "fly"},
    {"id": BIRDS_TOKEN_ID, "text": "Birds"},
)

ACCESSIBILITY = AccessibilityContract(
    accessible_equivalent="Named move controls and a submit control perform every token reorder and submission.",
    keyboard_policy="Keyboard buttons perform the same typed reorder and submit operations as pointer interaction.",
    touch_policy="Pointer interaction supports touch drag/drop with the same semantic reorder operation.",
    direction_policy="English academic tokens always render LTR; surrounding English or Arabic UI never changes token identity or order.",
    mobile_fallback="Narrow layouts retain the ordered LTR token row, named move controls, and a submit control.",
    safe_fallback="When interaction is unavailable, the renderer presents the ordered named tokens and accessible move controls.",
    reduced_motion_policy=ReducedMotionPolicy.OPTIONAL_WITH_STATIC_EQUIVALENT,
)

ACCESSIBILITY_PAYLOAD = {
    "accessible_equivalent": "named-token-move-controls",
    "keyboard_policy": "equivalent-typed-operation",
    "touch_policy": "pointer-drag-equivalent",
    "direction_policy": "academic-ltr-with-locale-aware-outer-ui",
    "reduced_motion_policy": "static-feedback-equivalent",
}


def sentence_ordering_scene_seed() -> dict[str, object]:
    """Return browser-safe fixture data without the server-owned answer order."""

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
    """Accept duplicate visible labels while rejecting unstable or duplicate durable identities."""

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
    _require_exact_keys(
        payload,
        {"fixture_key", "fixture_version", "token_schema_version", "tokens", "token_ids"},
        "Sentence ordering scene seed",
    )
    if payload.get("fixture_key") != FIXTURE_KEY or payload.get("fixture_version") != FIXTURE_VERSION:
        raise ValueError("Sentence ordering scene seed does not identify the approved fixture.")
    if payload.get("token_schema_version") != TOKEN_SCHEMA_VERSION:
        raise ValueError("Sentence ordering scene seed token schema is unsupported.")
    if validate_token_catalog(payload.get("tokens"), label="Sentence ordering scene seed") != list(_TOKEN_CATALOG):
        raise ValueError("Sentence ordering scene seed token catalog is unsupported.")
    if _token_ids(payload.get("token_ids"), label="Sentence ordering scene tokens") != list(_INITIAL_TOKEN_ORDER):
        raise ValueError("Sentence ordering scene seed order is unsupported.")


def validate_reorder_payload(payload: Mapping[str, object]) -> None:
    _require_exact_keys(payload, {"token_id", "from_index", "to_index"}, "Sentence ordering reorder payload")
    token_id, from_index, to_index = payload.get("token_id"), payload.get("from_index"), payload.get("to_index")
    if token_id not in _TOKEN_ID_SET:
        raise ValueError("Sentence ordering token identity is unsupported.")
    if any(type(index) is not int or index < 0 or index >= len(_TOKEN_ID_SET) for index in (from_index, to_index)):
        raise ValueError("Sentence ordering token positions are unsupported.")
    if from_index == to_index:
        raise ValueError("Sentence ordering reorder must change a token position.")


def validate_submit_payload(payload: Mapping[str, object]) -> None:
    _require_exact_keys(payload, {"token_ids"}, "Sentence ordering submit payload")
    _token_ids(payload.get("token_ids"), label="Sentence ordering submitted tokens")


def _state_token_ids(activity_state: Mapping[str, object]) -> list[str]:
    current = activity_state.get(ACTIVITY_KEY)
    if current is None:
        seed = activity_state.get("scene_seed")
        if not isinstance(seed, Mapping):
            raise ValueError("Sentence ordering authoritative scene seed is unavailable.")
        validate_scene_seed(seed)
        return _token_ids(seed.get("token_ids"), label="Sentence ordering scene tokens")
    if not isinstance(current, Mapping):
        raise ValueError("Sentence ordering activity state is unsupported.")
    return _token_ids(current.get("token_ids"), label="Sentence ordering activity tokens")


def validate_submit_configuration(payload: Mapping[str, object]) -> ValidationResult:
    """Validate the submitted server-state configuration against the authored fixture."""

    action = payload.get("action")
    activity_state = payload.get("activity_state")
    if not isinstance(action, Mapping) or not isinstance(activity_state, Mapping):
        raise ValueError("Sentence ordering submit validation requires authoritative activity state.")
    validate_submit_payload(action)
    submitted = _token_ids(action.get("token_ids"), label="Sentence ordering submitted tokens")
    if submitted != _state_token_ids(activity_state):
        return ValidationResult(
            ValidationStatus.INVALID,
            feedback_code="SUBMITTED_TOKEN_ORDER_DOES_NOT_MATCH_STATE",
            next_action_keys=(REORDER_TOKEN_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY),
        )
    if tuple(submitted) == _VALID_ORDER:
        return ValidationResult(ValidationStatus.VALID, feedback_code="SENTENCE_ORDER_COMPLETE")
    return ValidationResult(
        ValidationStatus.INVALID,
        feedback_code="SENTENCE_ORDER_NEEDS_REORDERING",
        next_action_keys=(REORDER_TOKEN_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY),
    )


def reduce_sentence_ordering(snapshot: dict[str, object], event: object) -> dict[str, object]:
    """Reduce only registered sentence-ordering semantic events."""

    sequence = getattr(event, "sequence", None)
    actor = getattr(event, "actor", None)
    action_key = getattr(event, "action_key", None)
    payload = getattr(event, "payload", None)
    event_id = getattr(event, "id", None)
    if not isinstance(sequence, int) or sequence <= int(snapshot["latest_event_sequence"]):
        raise ValueError("Sentence ordering event sequence must advance the Snapshot.")
    if not isinstance(payload, Mapping):
        raise ValueError("Sentence ordering event payload is unsupported.")
    next_snapshot = deepcopy(snapshot)
    next_snapshot["latest_event_sequence"] = sequence
    if actor == "STUDENT":
        next_snapshot["last_meaningful_student_event_id"] = event_id
    state_payload = dict(next_snapshot["state_payload"])
    token_ids = _state_token_ids(state_payload)
    if action_key == REORDER_TOKEN_ACTION_KEY:
        validate_reorder_payload(payload)
        token_id = payload["token_id"]
        from_index = payload["from_index"]
        to_index = payload["to_index"]
        if token_ids[from_index] != token_id:
            raise ValueError("Sentence ordering reorder source does not match authoritative state.")
        token_ids.pop(from_index)
        token_ids.insert(to_index, token_id)
    elif action_key == SUBMIT_CONFIGURATION_ACTION_KEY:
        validate_submit_payload(payload)
        if _token_ids(payload["token_ids"], label="Sentence ordering submitted tokens") != token_ids:
            raise ValueError("Sentence ordering submission does not match authoritative state.")
    else:
        raise ValueError("Sentence ordering action is unsupported by its reducer.")
    activity_state: dict[str, object] = {
        "fixture_key": FIXTURE_KEY,
        "fixture_version": FIXTURE_VERSION,
        "token_schema_version": TOKEN_SCHEMA_VERSION,
        "token_ids": token_ids,
    }
    if action_key == SUBMIT_CONFIGURATION_ACTION_KEY:
        activity_state["last_submission"] = {"token_ids": list(payload["token_ids"])}
    elif isinstance(state_payload.get(ACTIVITY_KEY), Mapping):
        previous_submission = state_payload[ACTIVITY_KEY].get("last_submission")
        if previous_submission is not None:
            activity_state["last_submission"] = deepcopy(previous_submission)
    state_payload[ACTIVITY_KEY] = activity_state
    next_snapshot["state_payload"] = state_payload
    return next_snapshot


def make_sentence_ordering_profile() -> SubjectCapabilityProfile:
    """Return exact ENGLISH v2 while retaining ENGLISH v1 for replay."""

    reorder = ActivityActionContract(
        action_key=REORDER_TOKEN_ACTION_KEY,
        event_kind=REORDER_EVENT_KIND,
        event_schema_version=REORDER_EVENT_SCHEMA_VERSION,
        payload_schema_version=REORDER_PAYLOAD_SCHEMA_VERSION,
        payload_validator_key="sentence-ordering-workspace-reorder-payload",
        interaction_policy=InteractionPolicy.RECORD_ONLY,
        semantic_validation_policy=SemanticValidationPolicy.NONE,
    )
    submit = ActivityActionContract(
        action_key=SUBMIT_CONFIGURATION_ACTION_KEY,
        event_kind=SUBMIT_EVENT_KIND,
        event_schema_version=SUBMIT_EVENT_SCHEMA_VERSION,
        payload_schema_version=SUBMIT_PAYLOAD_SCHEMA_VERSION,
        payload_validator_key="sentence-ordering-workspace-submit-payload",
        interaction_policy=InteractionPolicy.TUTOR_TRIGGERING,
        semantic_validation_policy=SemanticValidationPolicy.REQUIRED,
        interaction_kind=SUBMIT_INTERACTION_KIND,
        validator_key=SUBMIT_VALIDATOR_KEY,
        validator_version=SUBMIT_VALIDATOR_VERSION,
    )
    return SubjectCapabilityProfile(
        subject_key="ENGLISH",
        profile_version=ENGLISH_PROFILE_VERSION,
        supported_grade_scope=(),
        concept_namespace="lina.english.sentence-order",
        tutor_guidance_fragment="english-sentence-ordering-v1",
        grounding_policy_key="question-driven-grounding-v1",
        locale_policy_key="subject-independent-locale-v1",
        deterministic_fallback="safe-text-fallback-v1",
        canvas_specialist_profile_key=None,
        renderers=(
            RendererContract(
                renderer_key=RENDERER_KEY,
                renderer_version=RENDERER_VERSION,
                subject_key="ENGLISH",
                supported_activity_keys=(ACTIVITY_KEY,),
                scene_input_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
                interactive=True,
                supported_action_keys=(REORDER_TOKEN_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY),
                required_validator_keys=(SUBMIT_VALIDATOR_KEY,),
                state_adapter_key="sentence-ordering-workspace-state-v1",
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
                subject_key="ENGLISH",
                concept_namespace="lina.english.sentence-order",
                renderer_key=RENDERER_KEY,
                renderer_version=RENDERER_VERSION,
                initial_scene_payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
                initial_scene_payload_validator_key="sentence-ordering-workspace-scene-payload",
                actions=(reorder, submit),
                completion_semantics="A durable submitted token order validates the authored English sentence.",
                immediate_feedback_policy="Bounded validation feedback reflects durable state; color is never the only signal.",
                support_action_keys=(),
                fallback="Keep Tutor chat available and describe the declared English tokens when the renderer is unavailable.",
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
                payload_validator_key="sentence-ordering-workspace-scene-payload",
                payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
                validator=validate_scene_seed,
            ),
            PayloadValidatorContract(
                payload_validator_key="sentence-ordering-workspace-reorder-payload",
                payload_schema_version=REORDER_PAYLOAD_SCHEMA_VERSION,
                validator=validate_reorder_payload,
            ),
            PayloadValidatorContract(
                payload_validator_key="sentence-ordering-workspace-submit-payload",
                payload_schema_version=SUBMIT_PAYLOAD_SCHEMA_VERSION,
                validator=validate_submit_payload,
            ),
        ),
        reducers=(ReducerContract(REDUCER_KEY, REDUCER_VERSION, reduce_sentence_ordering),),
    )
