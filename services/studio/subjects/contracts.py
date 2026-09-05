"""Code-owned Subject Capability contracts for the subject-agnostic Studio Core."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Protocol


JsonPayload = Mapping[str, object]
PayloadValidator = Callable[[JsonPayload], None]


class ValidationStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNDER_SPECIFIED = "UNDER_SPECIFIED"
    VALID_ALTERNATIVE = "VALID_ALTERNATIVE"
    INCOMPLETE = "INCOMPLETE"


class ReducedMotionPolicy(str, Enum):
    NO_MOTION = "NO_MOTION"
    OPTIONAL_WITH_STATIC_EQUIVALENT = "OPTIONAL_WITH_STATIC_EQUIVALENT"
    REQUIRED_WITH_REDUCED_EQUIVALENT = "REQUIRED_WITH_REDUCED_EQUIVALENT"


class SemanticValidationPolicy(str, Enum):
    NONE = "NONE"
    REQUIRED = "REQUIRED"


MAX_ACTIVITY_ACTION_KEY_LENGTH = 128
MAX_VALIDATION_FEEDBACK_CODE_LENGTH = 128
MAX_VALIDATION_NEXT_ACTION_KEYS = 8


@dataclass(frozen=True)
class ValidationResult:
    status: ValidationStatus
    feedback_code: str | None = None
    next_action_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, ValidationStatus):
            raise ValueError("Validation result status must be a registered bounded status.")
        if self.feedback_code is not None and (
            not isinstance(self.feedback_code, str)
            or not self.feedback_code.strip()
            or len(self.feedback_code) > MAX_VALIDATION_FEEDBACK_CODE_LENGTH
        ):
            raise ValueError("Validation feedback code must be a bounded non-empty string.")
        if not isinstance(self.next_action_keys, tuple) or len(self.next_action_keys) > MAX_VALIDATION_NEXT_ACTION_KEYS:
            raise ValueError("Validation next action keys must be a bounded tuple.")
        for action_key in self.next_action_keys:
            if not isinstance(action_key, str) or not action_key.strip() or len(action_key) > MAX_ACTIVITY_ACTION_KEY_LENGTH:
                raise ValueError("Validation next action keys must be bounded non-empty strings.")


Validator = Callable[[JsonPayload], ValidationResult]


class ActivityReducer(Protocol):
    def __call__(self, snapshot: dict[str, object], event: object) -> dict[str, object]: ...


class InteractionPolicy(str, Enum):
    RECORD_ONLY = "RECORD_ONLY"
    TUTOR_TRIGGERING = "TUTOR_TRIGGERING"


@dataclass(frozen=True)
class AccessibilityContract:
    accessible_equivalent: str
    keyboard_policy: str
    touch_policy: str
    direction_policy: str
    mobile_fallback: str
    safe_fallback: str
    reduced_motion_policy: ReducedMotionPolicy

    def __post_init__(self) -> None:
        for value in (
            self.accessible_equivalent,
            self.keyboard_policy,
            self.touch_policy,
            self.direction_policy,
            self.mobile_fallback,
            self.safe_fallback,
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Renderer and Activity accessibility metadata must be explicit and non-empty.")
        if not isinstance(self.reduced_motion_policy, ReducedMotionPolicy):
            raise ValueError("Renderer reduced-motion policy must be a registered bounded policy.")


@dataclass(frozen=True)
class RendererContract:
    renderer_key: str
    renderer_version: str
    subject_key: str
    supported_activity_keys: tuple[str, ...]
    scene_input_schema_version: str
    interactive: bool
    supported_action_keys: tuple[str, ...]
    required_validator_keys: tuple[str, ...]
    state_adapter_key: str
    accessibility: AccessibilityContract
    source_view_compatible: bool
    annotation_compatible: bool
    reconstruction_compatible: bool
    implementation_status: str


@dataclass(frozen=True)
class ActivityActionContract:
    action_key: str
    event_kind: str
    event_schema_version: str
    payload_schema_version: str
    payload_validator_key: str
    interaction_policy: InteractionPolicy
    semantic_validation_policy: SemanticValidationPolicy
    interaction_kind: str | None = None
    validator_key: str | None = None
    validator_version: str | None = None

    def __post_init__(self) -> None:
        if self.interaction_policy is InteractionPolicy.TUTOR_TRIGGERING and not self.interaction_kind:
            raise ValueError("Tutor-triggering activity actions require a contract-owned interaction kind.")
        if self.interaction_policy is InteractionPolicy.RECORD_ONLY and self.interaction_kind is not None:
            raise ValueError("Record-only activity actions cannot declare a StudentInteraction kind.")
        if (self.validator_key is None) != (self.validator_version is None):
            raise ValueError("Semantic validators require an exact key and version pair.")
        if self.semantic_validation_policy is SemanticValidationPolicy.NONE and self.validator_key is not None:
            raise ValueError("Actions declaring no semantic validator cannot register one.")
        if self.semantic_validation_policy is SemanticValidationPolicy.REQUIRED and self.validator_key is None:
            raise ValueError("Actions requiring semantic validation need an exact validator key and version.")
        if not self.action_key or len(self.action_key) > MAX_ACTIVITY_ACTION_KEY_LENGTH:
            raise ValueError("Activity action keys must be bounded non-empty strings.")


@dataclass(frozen=True)
class ActivityContract:
    activity_key: str
    activity_version: str
    subject_key: str
    concept_namespace: str
    renderer_key: str
    renderer_version: str
    initial_scene_payload_schema_version: str
    initial_scene_payload_validator_key: str
    actions: tuple[ActivityActionContract, ...]
    completion_semantics: str
    immediate_feedback_policy: str
    support_action_keys: tuple[str, ...]
    fallback: str
    accessibility: AccessibilityContract
    reducer_key: str
    reducer_version: str
    requires_explicit_hint: bool = False


@dataclass(frozen=True)
class ValidatorContract:
    validator_key: str
    validator_version: str
    validator: Validator
    requires_activity_state: bool = False


@dataclass(frozen=True)
class PayloadValidatorContract:
    payload_validator_key: str
    payload_schema_version: str
    validator: PayloadValidator


@dataclass(frozen=True)
class ReducerContract:
    reducer_key: str
    reducer_version: str
    reducer: ActivityReducer


@dataclass(frozen=True)
class SubjectCapabilityProfile:
    subject_key: str
    profile_version: str
    supported_grade_scope: tuple[str, ...]
    concept_namespace: str
    tutor_guidance_fragment: str
    grounding_policy_key: str
    locale_policy_key: str
    deterministic_fallback: str
    canvas_specialist_profile_key: str | None
    activities: tuple[ActivityContract, ...] = ()
    renderers: tuple[RendererContract, ...] = ()
    validators: tuple[ValidatorContract, ...] = ()
    payload_validators: tuple[PayloadValidatorContract, ...] = ()
    reducers: tuple[ReducerContract, ...] = ()
