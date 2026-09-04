"""Versioned educational Workspace requests emitted by the primary Tutor call."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


WORKSPACE_INTENT_VERSION = "workspace-intent-v1"
MAX_CONCEPT_KEYS = 6
MAX_CONCEPT_KEY_LENGTH = 128
MAX_SUBJECT_KEY_LENGTH = 64
MAX_LEARNING_GOAL_LENGTH = 500
MAX_ACTIVITY_HINT_LENGTH = 160
MAX_SOURCE_REFERENCES = 6
MAX_SOURCE_REFERENCE_LENGTH = 256
MAX_SAFE_TEXT_FALLBACK_LENGTH = 500


class WorkspaceIntentContractError(ValueError):
    """The primary Tutor output contains an unsafe or malformed Workspace request."""


class WorkspaceIntentAction(str, Enum):
    NO_CHANGE = "NO_CHANGE"
    OPEN_ACTIVITY = "OPEN_ACTIVITY"
    UPDATE_ACTIVITY = "UPDATE_ACTIVITY"
    CLOSE_ACTIVITY = "CLOSE_ACTIVITY"
    FOCUS_SOURCE = "FOCUS_SOURCE"
    REQUEST_ANNOTATION = "REQUEST_ANNOTATION"
    REQUEST_CUSTOM_COMPOSE = "REQUEST_CUSTOM_COMPOSE"


class RepresentationNeed(str, Enum):
    NONE = "NONE"
    SOURCE = "SOURCE"
    ANNOTATION = "ANNOTATION"
    VISUAL = "VISUAL"
    INTERACTIVE = "INTERACTIVE"
    CUSTOM_COMPOSITION = "CUSTOM_COMPOSITION"


class ExpectedStudentResponseMode(str, Enum):
    NONE = "NONE"
    CHAT = "CHAT"
    WORKSPACE = "WORKSPACE"
    EITHER = "EITHER"
    OBSERVE_ONLY = "OBSERVE_ONLY"


class PresentationSequence(str, Enum):
    TEXT_FIRST = "TEXT_FIRST"
    WORKSPACE_FIRST = "WORKSPACE_FIRST"
    PARALLEL = "PARALLEL"


_IMPLEMENTATION_TERMS = (
    "renderer",
    "react",
    "svg",
    "jsxgraph",
    "konva",
    "mathlive",
    "component",
    "provider",
    "model",
    "tool",
    "event_kind",
    "reducer",
    "validator",
    "scene id",
    "scene_id",
)


def _is_plain_student_safe_text(value: str) -> bool:
    normalized = value.casefold()
    return not any(
        token in normalized
        for token in ("http://", "https://", "www.", "`", "```", "<script", "{", "}")
    )


def _is_educational_description(value: str) -> bool:
    normalized = value.casefold()
    return _is_plain_student_safe_text(value) and not any(term in normalized for term in _IMPLEMENTATION_TERMS)


class WorkspaceIntent(BaseModel):
    """Bounded educational need, never an instruction to mutate or implement Studio."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: Literal[WORKSPACE_INTENT_VERSION]
    action: WorkspaceIntentAction
    subject_key: str | None = Field(default=None, min_length=1, max_length=MAX_SUBJECT_KEY_LENGTH)
    concept_keys: list[str] = Field(default_factory=list, max_length=MAX_CONCEPT_KEYS)
    learning_goal: str | None = Field(default=None, min_length=1, max_length=MAX_LEARNING_GOAL_LENGTH)
    activity_hint: str | None = Field(default=None, min_length=1, max_length=MAX_ACTIVITY_HINT_LENGTH)
    representation_need: RepresentationNeed
    expected_student_response_mode: ExpectedStudentResponseMode
    presentation_sequence: PresentationSequence
    source_references: list[str] = Field(default_factory=list, max_length=MAX_SOURCE_REFERENCES)
    safe_text_fallback: str | None = Field(default=None, min_length=1, max_length=MAX_SAFE_TEXT_FALLBACK_LENGTH)

    @field_validator("concept_keys")
    @classmethod
    def concept_keys_are_bounded_and_unique(cls, value: list[str]) -> list[str]:
        if any(not key.strip() or len(key) > MAX_CONCEPT_KEY_LENGTH for key in value):
            raise ValueError("Workspace concept keys must be bounded non-empty strings.")
        if len({key.casefold() for key in value}) != len(value):
            raise ValueError("Workspace concept keys must be unique.")
        return value

    @field_validator("source_references")
    @classmethod
    def source_references_are_bounded_and_unique(cls, value: list[str]) -> list[str]:
        if any(not ref.strip() or len(ref) > MAX_SOURCE_REFERENCE_LENGTH for ref in value):
            raise ValueError("Workspace source references must be bounded non-empty strings.")
        if len(set(value)) != len(value):
            raise ValueError("Workspace source references must be unique.")
        return value

    @model_validator(mode="after")
    def educational_fields_cannot_control_implementation(self) -> "WorkspaceIntent":
        for value in (self.learning_goal, self.activity_hint, self.safe_text_fallback):
            if value is not None and not _is_educational_description(value):
                raise ValueError("Workspace intent text must remain plain educational content.")
        if self.safe_text_fallback is not None and not _is_plain_student_safe_text(self.safe_text_fallback):
            raise ValueError("Workspace fallback must be plain Student-safe text.")
        return self


def parse_workspace_intent(payload: object) -> WorkspaceIntent | None:
    """Accept null or exactly one strict, versioned WorkspaceIntent."""

    if payload is None:
        return None
    try:
        return WorkspaceIntent.model_validate(payload)
    except ValidationError as error:
        raise WorkspaceIntentContractError("Workspace intent violates the contract.") from error


def workspace_intent_output_schema() -> dict[str, object]:
    """Return the provider-facing strict schema without exposing implementation details."""

    return {
        "anyOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "version": {"type": "string", "enum": [WORKSPACE_INTENT_VERSION]},
                    "action": {"type": "string", "enum": [item.value for item in WorkspaceIntentAction]},
                    "subject_key": {"type": ["string", "null"], "minLength": 1, "maxLength": MAX_SUBJECT_KEY_LENGTH},
                    "concept_keys": {"type": "array", "maxItems": MAX_CONCEPT_KEYS, "items": {"type": "string", "minLength": 1, "maxLength": MAX_CONCEPT_KEY_LENGTH}},
                    "learning_goal": {"type": ["string", "null"], "minLength": 1, "maxLength": MAX_LEARNING_GOAL_LENGTH},
                    "activity_hint": {"type": ["string", "null"], "minLength": 1, "maxLength": MAX_ACTIVITY_HINT_LENGTH},
                    "representation_need": {"type": "string", "enum": [item.value for item in RepresentationNeed]},
                    "expected_student_response_mode": {"type": "string", "enum": [item.value for item in ExpectedStudentResponseMode]},
                    "presentation_sequence": {"type": "string", "enum": [item.value for item in PresentationSequence]},
                    "source_references": {"type": "array", "maxItems": MAX_SOURCE_REFERENCES, "items": {"type": "string", "minLength": 1, "maxLength": MAX_SOURCE_REFERENCE_LENGTH}},
                    "safe_text_fallback": {"type": ["string", "null"], "minLength": 1, "maxLength": MAX_SAFE_TEXT_FALLBACK_LENGTH},
                },
                "required": [
                    "version", "action", "subject_key", "concept_keys", "learning_goal", "activity_hint",
                    "representation_need", "expected_student_response_mode", "presentation_sequence",
                    "source_references", "safe_text_fallback",
                ],
            },
            {"type": "null"},
        ]
    }
