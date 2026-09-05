"""Exact production contracts for the bounded Science filtration sequence activity."""

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


SCIENCE_PROFILE_VERSION = "subject-profile-v2"
ACTIVITY_KEY = "process_sequence_workspace"
ACTIVITY_VERSION = "process-sequence-workspace-activity-v1"
RENDERER_KEY = "process-sequence-workspace"
RENDERER_VERSION = "process-sequence-workspace-renderer-v1"
SCENE_PAYLOAD_SCHEMA_VERSION = "process-sequence-workspace-scene-v1"
REORDER_STAGE_ACTION_KEY = "REORDER_STAGE"
SUBMIT_CONFIGURATION_ACTION_KEY = "SUBMIT_CONFIGURATION"
REORDER_PAYLOAD_SCHEMA_VERSION = "process-sequence-workspace-reorder-v1"
SUBMIT_PAYLOAD_SCHEMA_VERSION = "process-sequence-workspace-submit-v1"
REORDER_EVENT_SCHEMA_VERSION = "process-sequence-workspace-event-v1"
SUBMIT_EVENT_SCHEMA_VERSION = "process-sequence-workspace-event-v1"
REORDER_EVENT_KIND = "science.process_sequence_workspace.stage_reordered"
SUBMIT_EVENT_KIND = "science.process_sequence_workspace.configuration_submitted"
SUBMIT_INTERACTION_KIND = "SCIENCE_PROCESS_SEQUENCE_WORKSPACE_SUBMISSION"
REDUCER_KEY = "process-sequence-workspace-reducer"
REDUCER_VERSION = "process-sequence-workspace-reducer-v1"
SUBMIT_VALIDATOR_KEY = "process-sequence-workspace-submit-validator"
SUBMIT_VALIDATOR_VERSION = "process-sequence-workspace-submit-validator-v1"
FIXTURE_KEY = "sand_water_filtration"
FIXTURE_VERSION = "sand-water-filtration-fixture-v1"

PREPARE_FILTER_STAGE_ID = "prepare-filter-funnel"
POUR_MIXTURE_STAGE_ID = "pour-sand-water-mixture"
ALLOW_FILTER_STAGE_ID = "allow-water-to-filter"
COLLECT_WATER_STAGE_ID = "collect-filtered-water"
_STAGE_IDS = (
    PREPARE_FILTER_STAGE_ID,
    POUR_MIXTURE_STAGE_ID,
    ALLOW_FILTER_STAGE_ID,
    COLLECT_WATER_STAGE_ID,
)
_VALID_ORDER = _STAGE_IDS
_INITIAL_STAGE_ORDER = (
    ALLOW_FILTER_STAGE_ID,
    PREPARE_FILTER_STAGE_ID,
    COLLECT_WATER_STAGE_ID,
    POUR_MIXTURE_STAGE_ID,
)
_STAGE_CATALOG = (
    {
        "id": ALLOW_FILTER_STAGE_ID,
        "label_en": "Let the water pass through the filter",
        "label_ar": "اترك الماء يمر عبر المرشح",
    },
    {
        "id": COLLECT_WATER_STAGE_ID,
        "label_en": "Collect the filtered water",
        "label_ar": "اجمع الماء المُرشَّح",
    },
    {
        "id": PREPARE_FILTER_STAGE_ID,
        "label_en": "Set the filter paper in the funnel",
        "label_ar": "جهّز القمع وورق الترشيح",
    },
    {
        "id": POUR_MIXTURE_STAGE_ID,
        "label_en": "Pour the sand-and-water mixture",
        "label_ar": "اسكب خليط الرمل والماء",
    },
)

ACCESSIBILITY = AccessibilityContract(
    accessible_equivalent="Named move controls and a submit control perform every stage reorder and submission.",
    keyboard_policy="Keyboard buttons perform the same typed reorder and submit operations as pointer interaction.",
    touch_policy="Pointer interaction supports touch drag/drop with the same semantic reorder operation.",
    direction_policy="The renderer accepts English, Arabic, and mixed-direction stage presentation without changing stage identity.",
    mobile_fallback="Narrow layouts retain ordered labels, named move controls, and a submit control.",
    safe_fallback="When interaction is unavailable, the renderer presents the ordered named stages and accessible move controls.",
    reduced_motion_policy=ReducedMotionPolicy.OPTIONAL_WITH_STATIC_EQUIVALENT,
)

ACCESSIBILITY_PAYLOAD = {
    "accessible_equivalent": "named-stage-move-controls",
    "keyboard_policy": "equivalent-typed-operation",
    "touch_policy": "pointer-drag-equivalent",
    "direction_policy": "locale-and-direction-aware",
    "reduced_motion_policy": "static-feedback-equivalent",
}


def process_sequence_scene_seed() -> dict[str, object]:
    """Return browser-safe fixture data without the server-owned answer order."""

    return {
        "fixture_key": FIXTURE_KEY,
        "fixture_version": FIXTURE_VERSION,
        "stages": deepcopy(list(_STAGE_CATALOG)),
        "stage_ids": list(_INITIAL_STAGE_ORDER),
    }


def _require_exact_keys(payload: Mapping[str, object], expected: set[str], label: str) -> None:
    if set(payload) != expected:
        raise ValueError(f"{label} has an unsupported shape.")


def _stage_ids(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(stage_id, str) and stage_id for stage_id in value):
        raise ValueError(f"{label} must be a list of stable stage identities.")
    if len(value) != len(_STAGE_IDS) or set(value) != set(_STAGE_IDS):
        raise ValueError(f"{label} must contain every known stage exactly once.")
    return list(value)


def validate_scene_seed(payload: Mapping[str, object]) -> None:
    _require_exact_keys(payload, {"fixture_key", "fixture_version", "stages", "stage_ids"}, "Process sequence scene seed")
    if payload.get("fixture_key") != FIXTURE_KEY or payload.get("fixture_version") != FIXTURE_VERSION:
        raise ValueError("Process sequence scene seed does not identify the approved fixture.")
    stages = payload.get("stages")
    if not isinstance(stages, list) or stages != list(_STAGE_CATALOG):
        raise ValueError("Process sequence scene seed stage catalog is unsupported.")
    if _stage_ids(payload.get("stage_ids"), label="Process sequence scene stages") != list(_INITIAL_STAGE_ORDER):
        raise ValueError("Process sequence scene seed order is unsupported.")


def validate_reorder_payload(payload: Mapping[str, object]) -> None:
    _require_exact_keys(payload, {"stage_id", "from_index", "to_index"}, "Process sequence reorder payload")
    stage_id, from_index, to_index = payload.get("stage_id"), payload.get("from_index"), payload.get("to_index")
    if stage_id not in _STAGE_IDS:
        raise ValueError("Process sequence stage identity is unsupported.")
    if any(type(index) is not int or index < 0 or index >= len(_STAGE_IDS) for index in (from_index, to_index)):
        raise ValueError("Process sequence stage positions are unsupported.")
    if from_index == to_index:
        raise ValueError("Process sequence reorder must change a stage position.")


def validate_submit_payload(payload: Mapping[str, object]) -> None:
    _require_exact_keys(payload, {"stage_ids"}, "Process sequence submit payload")
    _stage_ids(payload.get("stage_ids"), label="Process sequence submitted stages")


def _state_stage_ids(activity_state: Mapping[str, object]) -> list[str]:
    current = activity_state.get(ACTIVITY_KEY)
    if current is None:
        seed = activity_state.get("scene_seed")
        if not isinstance(seed, Mapping):
            raise ValueError("Process sequence authoritative scene seed is unavailable.")
        validate_scene_seed(seed)
        return _stage_ids(seed.get("stage_ids"), label="Process sequence scene stages")
    if not isinstance(current, Mapping):
        raise ValueError("Process sequence activity state is unsupported.")
    return _stage_ids(current.get("stage_ids"), label="Process sequence activity stages")


def validate_submit_configuration(payload: Mapping[str, object]) -> ValidationResult:
    """Validate the submitted server-state configuration against the authored fixture."""

    action = payload.get("action")
    activity_state = payload.get("activity_state")
    if not isinstance(action, Mapping) or not isinstance(activity_state, Mapping):
        raise ValueError("Process sequence submit validation requires authoritative activity state.")
    validate_submit_payload(action)
    submitted = _stage_ids(action.get("stage_ids"), label="Process sequence submitted stages")
    if submitted != _state_stage_ids(activity_state):
        # At append time the reducer below independently rejects a mismatch,
        # so it cannot mutate state. Returning bounded feedback here also lets
        # Runtime-03 inspect an immutable source submission after a later
        # record-only reorder has changed the current snapshot.
        return ValidationResult(
            ValidationStatus.INVALID,
            feedback_code="SUBMITTED_SEQUENCE_DOES_NOT_MATCH_STATE",
            next_action_keys=(REORDER_STAGE_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY),
        )
    if tuple(submitted) == _VALID_ORDER:
        return ValidationResult(ValidationStatus.VALID, feedback_code="FILTRATION_SEQUENCE_COMPLETE")
    return ValidationResult(
        ValidationStatus.INVALID,
        feedback_code="FILTRATION_SEQUENCE_NEEDS_REORDERING",
        next_action_keys=(REORDER_STAGE_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY),
    )


def reduce_process_sequence(snapshot: dict[str, object], event: object) -> dict[str, object]:
    """Reduce only this activity's registered semantic events."""

    sequence = getattr(event, "sequence", None)
    actor = getattr(event, "actor", None)
    action_key = getattr(event, "action_key", None)
    payload = getattr(event, "payload", None)
    event_id = getattr(event, "id", None)
    if not isinstance(sequence, int) or sequence <= int(snapshot["latest_event_sequence"]):
        raise ValueError("Process sequence event sequence must advance the Snapshot.")
    if not isinstance(payload, Mapping):
        raise ValueError("Process sequence event payload is unsupported.")
    next_snapshot = deepcopy(snapshot)
    next_snapshot["latest_event_sequence"] = sequence
    if actor == "STUDENT":
        next_snapshot["last_meaningful_student_event_id"] = event_id
    state_payload = dict(next_snapshot["state_payload"])
    stage_ids = _state_stage_ids(state_payload)
    if action_key == REORDER_STAGE_ACTION_KEY:
        validate_reorder_payload(payload)
        stage_id = payload["stage_id"]
        from_index = payload["from_index"]
        to_index = payload["to_index"]
        if stage_ids[from_index] != stage_id:
            raise ValueError("Process sequence reorder source does not match authoritative state.")
        stage_ids.pop(from_index)
        stage_ids.insert(to_index, stage_id)
    elif action_key == SUBMIT_CONFIGURATION_ACTION_KEY:
        validate_submit_payload(payload)
        if _stage_ids(payload["stage_ids"], label="Process sequence submitted stages") != stage_ids:
            raise ValueError("Process sequence submission does not match authoritative state.")
    else:
        raise ValueError("Process sequence action is unsupported by its reducer.")
    activity_state: dict[str, object] = {
        "fixture_key": FIXTURE_KEY,
        "fixture_version": FIXTURE_VERSION,
        "stage_ids": stage_ids,
    }
    if action_key == SUBMIT_CONFIGURATION_ACTION_KEY:
        activity_state["last_submission"] = {"stage_ids": list(payload["stage_ids"])}
    elif isinstance(state_payload.get(ACTIVITY_KEY), Mapping):
        previous_submission = state_payload[ACTIVITY_KEY].get("last_submission")
        if previous_submission is not None:
            activity_state["last_submission"] = deepcopy(previous_submission)
    state_payload[ACTIVITY_KEY] = activity_state
    next_snapshot["state_payload"] = state_payload
    return next_snapshot


def make_process_sequence_profile() -> SubjectCapabilityProfile:
    """Return the exact SCIENCE v2 profile while retaining SCIENCE v1 for replay."""

    reorder = ActivityActionContract(
        action_key=REORDER_STAGE_ACTION_KEY,
        event_kind=REORDER_EVENT_KIND,
        event_schema_version=REORDER_EVENT_SCHEMA_VERSION,
        payload_schema_version=REORDER_PAYLOAD_SCHEMA_VERSION,
        payload_validator_key="process-sequence-workspace-reorder-payload",
        interaction_policy=InteractionPolicy.RECORD_ONLY,
        semantic_validation_policy=SemanticValidationPolicy.NONE,
    )
    submit = ActivityActionContract(
        action_key=SUBMIT_CONFIGURATION_ACTION_KEY,
        event_kind=SUBMIT_EVENT_KIND,
        event_schema_version=SUBMIT_EVENT_SCHEMA_VERSION,
        payload_schema_version=SUBMIT_PAYLOAD_SCHEMA_VERSION,
        payload_validator_key="process-sequence-workspace-submit-payload",
        interaction_policy=InteractionPolicy.TUTOR_TRIGGERING,
        semantic_validation_policy=SemanticValidationPolicy.REQUIRED,
        interaction_kind=SUBMIT_INTERACTION_KIND,
        validator_key=SUBMIT_VALIDATOR_KEY,
        validator_version=SUBMIT_VALIDATOR_VERSION,
    )
    return SubjectCapabilityProfile(
        subject_key="SCIENCE",
        profile_version=SCIENCE_PROFILE_VERSION,
        supported_grade_scope=(),
        concept_namespace="lina.science.filtration",
        tutor_guidance_fragment="science-filtration-sequence-v1",
        grounding_policy_key="question-driven-grounding-v1",
        locale_policy_key="subject-independent-locale-v1",
        deterministic_fallback="safe-text-fallback-v1",
        canvas_specialist_profile_key=None,
        renderers=(
            RendererContract(
                renderer_key=RENDERER_KEY,
                renderer_version=RENDERER_VERSION,
                subject_key="SCIENCE",
                supported_activity_keys=(ACTIVITY_KEY,),
                scene_input_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
                interactive=True,
                supported_action_keys=(REORDER_STAGE_ACTION_KEY, SUBMIT_CONFIGURATION_ACTION_KEY),
                required_validator_keys=(SUBMIT_VALIDATOR_KEY,),
                state_adapter_key="process-sequence-workspace-state-v1",
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
                subject_key="SCIENCE",
                concept_namespace="lina.science.filtration",
                renderer_key=RENDERER_KEY,
                renderer_version=RENDERER_VERSION,
                initial_scene_payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
                initial_scene_payload_validator_key="process-sequence-workspace-scene-payload",
                actions=(reorder, submit),
                completion_semantics="A durable submitted filtration sequence validates the authored process order.",
                immediate_feedback_policy="Bounded validation feedback reflects durable state; color is never the only signal.",
                support_action_keys=(),
                fallback="Keep Tutor chat available and describe the named filtration stages when the renderer is unavailable.",
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
                payload_validator_key="process-sequence-workspace-scene-payload",
                payload_schema_version=SCENE_PAYLOAD_SCHEMA_VERSION,
                validator=validate_scene_seed,
            ),
            PayloadValidatorContract(
                payload_validator_key="process-sequence-workspace-reorder-payload",
                payload_schema_version=REORDER_PAYLOAD_SCHEMA_VERSION,
                validator=validate_reorder_payload,
            ),
            PayloadValidatorContract(
                payload_validator_key="process-sequence-workspace-submit-payload",
                payload_schema_version=SUBMIT_PAYLOAD_SCHEMA_VERSION,
                validator=validate_submit_payload,
            ),
        ),
        reducers=(ReducerContract(REDUCER_KEY, REDUCER_VERSION, reduce_process_sequence),),
    )
