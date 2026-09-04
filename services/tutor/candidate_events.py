"""Versioned, source-linked Candidate Event contract for one Tutor turn."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from services.tutor.teaching_decisions import PriorMethodRelation, TeachingMode, TeachingStrategy
from services.tutor.teaching_methods import ACTIVE_TEACHING_METHODS
from services.tutor.parent_boundaries import (
    PARENT_BOUNDARY_SCHEMA_VERSION,
    ParentBoundaryCategory,
    ParentBoundaryModelAction,
)
from services.intelligence.subjects import BROAD_SUBJECT_KEYS
from services.studio.workspace_intent import workspace_intent_output_schema


CANDIDATE_EVENT_SCHEMA_VERSION = "candidate-event-v1"
MISCONCEPTION_EVIDENCE_SCHEMA_VERSION = "misconception-evidence-v1"
TUTOR_TURN_SCHEMA_VERSION = "tutor_turn_v9"
TUTOR_TURN_SCHEMA_VERSIONS_WITH_PROVISIONAL_BROAD_SUBJECT = frozenset({
    "tutor_turn_v8",
    TUTOR_TURN_SCHEMA_VERSION,
})
MAX_SUGGESTED_ACTIONS = 4
MAX_GUIDED_CHECK_CHOICES = 4
CandidateEventType = Literal[
    "learning_attempt",
    "independent_success",
    "guided_success",
    "incorrect_attempt",
    "misconception_signal",
    "self_correction",
    "explanation_attempt",
    "transfer_attempt",
    "retention_check",
    "strategy_applied",
    "strategy_outcome",
    "support_change",
    "open_loop_created",
    "open_loop_resolved",
    "extended_learning_event",
]
# Old persisted Candidate Events may retain this historical event type for
# audit and bounded reprocessing, but new Tutor metadata must not emit it.
HistoricalCandidateEventType = CandidateEventType | Literal["current_focus_signal"]


class CandidateEventContractError(ValueError):
    """The Tutor's hidden Candidate Event metadata is not safe to persist."""


class SuggestedActionKind(str, Enum):
    NAVIGATION = "NAVIGATION"
    ANSWER_CHOICE = "ANSWER_CHOICE"


class SuggestedAction(BaseModel):
    """One explicit, server-persisted Student interaction option."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str = Field(min_length=1, max_length=120)
    kind: SuggestedActionKind


class GuidedLearningCheckChoice(BaseModel):
    """One visible answer choice for a concrete Tutor learning check."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str = Field(min_length=1, max_length=120)


class GuidedLearningCheck(BaseModel):
    """Model-proposed check content; the durable identity remains server-owned."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    prompt: str = Field(min_length=1, max_length=500)
    choices: list[GuidedLearningCheckChoice] = Field(min_length=2, max_length=MAX_GUIDED_CHECK_CHOICES)

    @model_validator(mode="after")
    def choices_are_unique_and_safe(self) -> "GuidedLearningCheck":
        labels = [choice.label.casefold() for choice in self.choices]
        if len(set(labels)) != len(labels):
            raise ValueError("Guided learning check choices must be unique.")
        if _contains_action_markup_or_url(self.prompt) or any(
            _contains_action_markup_or_url(choice.label) for choice in self.choices
        ):
            raise ValueError("Guided learning check contains unsupported markup or URL content.")
        return self


class PersistedGuidedLearningCheck(GuidedLearningCheck):
    """A validated check with an application-generated durable identity."""

    id: UUID


class MisconceptionEvidence(BaseModel):
    """Auditable Student-source grounding for one proposed misconception Candidate."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: Literal[MISCONCEPTION_EVIDENCE_SCHEMA_VERSION]
    incorrect_model: str = Field(min_length=1, max_length=500)
    explicit_student_reasoning: str = Field(min_length=1, max_length=500)
    source_message_id: UUID


class CandidateEventMetadataItem(BaseModel):
    """One potential learning signal, not a conclusion about the Student."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_type: CandidateEventType
    concept_ref: str | None = Field(default=None, min_length=1, max_length=128)
    summary: str = Field(min_length=1, max_length=500)
    signal: str = Field(min_length=1, max_length=128)
    source_message_ids: list[UUID] = Field(min_length=1, max_length=4)
    school_or_extended: Literal["school", "extended"]
    observed_student_outcome: str | None = Field(default=None, min_length=1, max_length=500)
    # Keep this raw until the runtime validates it against the current raw Student source.
    # That allows one invalid misconception candidate to be filtered without rejecting
    # other valid candidates in the same model metadata envelope.
    misconception_evidence: Any | None = None

    @model_validator(mode="after")
    def strategy_outcomes_require_an_observed_student_result(self) -> "CandidateEventMetadataItem":
        if self.event_type == "strategy_outcome" and self.observed_student_outcome is None:
            raise ValueError("strategy_outcome requires an observed_student_outcome.")
        if self.event_type == "extended_learning_event" and self.school_or_extended != "extended":
            raise ValueError("extended_learning_event must be marked extended.")
        return self


class CandidateEventMetadata(BaseModel):
    """The compact hidden metadata emitted alongside one student-facing reply."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[CANDIDATE_EVENT_SCHEMA_VERSION]
    candidates: list[CandidateEventMetadataItem] = Field(max_length=4)


def parse_candidate_event_metadata(
    payload: object,
    *,
    allowed_source_message_ids: set[UUID],
) -> CandidateEventMetadata:
    """Validate model meaning deterministically before Candidate Event persistence."""

    try:
        metadata = CandidateEventMetadata.model_validate(payload)
    except ValidationError as error:
        raise CandidateEventContractError("Candidate metadata violates the contract.") from error
    candidates: list[CandidateEventMetadataItem] = []
    for candidate in metadata.candidates:
        source_ids = set(candidate.source_message_ids)
        if not source_ids.issubset(allowed_source_message_ids):
            if candidate.event_type == "misconception_signal":
                continue
            raise CandidateEventContractError("Candidate metadata references an unavailable raw message.")
        candidates.append(candidate)
    return metadata.model_copy(update={"candidates": candidates})


def normalize_suggested_actions(payload: object) -> list[SuggestedAction]:
    """Keep completed Tutor action choices small, visible, and safe to show to a Student."""

    if not isinstance(payload, list):
        return []
    actions: list[SuggestedAction] = []
    for item in payload:
        try:
            action = SuggestedAction.model_validate(item)
        except ValidationError:
            continue
        if _contains_action_markup_or_url(action.label):
            continue
        actions.append(action)
        if len(actions) == MAX_SUGGESTED_ACTIONS:
            break
    return actions


def normalize_guided_learning_check(payload: object) -> GuidedLearningCheck | None:
    """Accept only one compact, concrete model-proposed check structure."""

    if payload is None:
        return None
    try:
        return GuidedLearningCheck.model_validate(payload)
    except ValidationError:
        return None


def persisted_guided_learning_check(payload: object) -> PersistedGuidedLearningCheck | None:
    """Read a server-generated check binding from a persisted Tutor message."""

    if not isinstance(payload, dict):
        return None
    try:
        return PersistedGuidedLearningCheck.model_validate(payload)
    except ValidationError:
        return None


def _contains_action_markup_or_url(action: str) -> bool:
    normalized = action.casefold()
    return (
        "http://" in normalized
        or "https://" in normalized
        or "www." in normalized
        or "`" in action
        or "**" in action
        or "[" in action
        or "](" in action
        or "#" in action
        or "{" in action
        or "}" in action
        or "candidate_metadata" in normalized
        or "source_message_id" in normalized
    )


TUTOR_OUTPUT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "text": {"type": "string"},
        "suggested_actions": {
            "type": "array",
            "maxItems": MAX_SUGGESTED_ACTIONS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "label": {"type": "string"},
                    "kind": {"type": "string", "enum": [kind.value for kind in SuggestedActionKind]},
                },
                "required": ["label", "kind"],
            },
        },
        "guided_check": {
            "anyOf": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "prompt": {"type": "string", "minLength": 1, "maxLength": 500},
                        "choices": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": MAX_GUIDED_CHECK_CHOICES,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {"label": {"type": "string", "minLength": 1, "maxLength": 120}},
                                "required": ["label"],
                            },
                        },
                    },
                    "required": ["prompt", "choices"],
                },
                {"type": "null"},
            ],
        },
        "teaching_mode": {"type": ["string", "null"], "enum": [*(mode.value for mode in TeachingMode), None]},
        "teaching_strategy": {"type": ["string", "null"], "enum": [*(strategy.value for strategy in TeachingStrategy), None]},
        "teaching_method_id": {"type": ["string", "null"], "enum": [*(method.value for method in ACTIVE_TEACHING_METHODS), None]},
        "prior_method_relation": {"type": ["string", "null"], "enum": [*(relation.value for relation in PriorMethodRelation), None]},
        "segment_relation": {"type": ["string", "null"], "enum": ["CONTINUE", "NEW_SEGMENT", "UNCERTAIN", None]},
        "structured_segment_state": {
            "anyOf": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "schema_version": {"type": "string", "enum": ["structured-segment-state-v1"]},
                        "active_goal": {"type": ["string", "null"], "maxLength": 500},
                        "unresolved_point": {"type": ["string", "null"], "maxLength": 500},
                        "active_references": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 500}},
                        "established_facts": {"type": "array", "maxItems": 6, "items": {"type": "string", "maxLength": 500}},
                        "source_message_ids": {"type": "array", "minItems": 1, "maxItems": 8, "items": {"type": "string"}},
                    },
                    "required": ["schema_version", "active_goal", "unresolved_point", "active_references", "established_facts", "source_message_ids"],
                },
                {"type": "null"},
            ]
        },
        "parent_boundary": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "schema_version": {"type": "string", "enum": [PARENT_BOUNDARY_SCHEMA_VERSION]},
                "category": {
                    "type": ["string", "null"],
                    "enum": [*(category.value for category in ParentBoundaryCategory), None],
                },
                "applies": {"type": "boolean"},
                "model_action": {
                    "type": "string",
                    "enum": [*(action.value for action in ParentBoundaryModelAction)],
                },
                "redirect": {
                    "anyOf": [
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "acknowledgement": {"type": "string", "minLength": 1, "maxLength": 160},
                                "parent_reference": {"type": "string", "minLength": 1, "maxLength": 160},
                                "safe_offer": {"type": "string", "minLength": 1, "maxLength": 160},
                            },
                            "required": ["acknowledgement", "parent_reference", "safe_offer"],
                        },
                        {"type": "null"},
                    ],
                },
            },
            "required": ["schema_version", "category", "applies", "model_action", "redirect"],
        },
        "candidate_metadata": {
            "anyOf": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "version": {"type": "string", "enum": [CANDIDATE_EVENT_SCHEMA_VERSION]},
                        "candidates": {
                            "type": "array",
                            "maxItems": 4,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "event_type": {"type": "string", "enum": list(CandidateEventType.__args__)},
                                    "concept_ref": {"type": ["string", "null"], "minLength": 1, "maxLength": 128},
                                    "summary": {"type": "string", "minLength": 1, "maxLength": 500},
                                    "signal": {"type": "string", "minLength": 1, "maxLength": 128},
                                    "source_message_ids": {
                                        "type": "array",
                                        "minItems": 1,
                                        "maxItems": 4,
                                        "items": {"type": "string", "format": "uuid"},
                                    },
                                    "school_or_extended": {"type": "string", "enum": ["school", "extended"]},
                                    "observed_student_outcome": {"type": ["string", "null"], "minLength": 1, "maxLength": 500},
                                    "misconception_evidence": {
                                        "anyOf": [
                                            {
                                                "type": "object",
                                                "additionalProperties": False,
                                                "properties": {
                                                    "version": {"type": "string", "enum": [MISCONCEPTION_EVIDENCE_SCHEMA_VERSION]},
                                                    "incorrect_model": {"type": "string", "minLength": 1, "maxLength": 500},
                                                    "explicit_student_reasoning": {"type": "string", "minLength": 1, "maxLength": 500},
                                                    "source_message_id": {"type": "string"},
                                                },
                                                "required": ["version", "incorrect_model", "explicit_student_reasoning", "source_message_id"],
                                            },
                                            {"type": "null"},
                                        ],
                                    },
                                },
                                "required": [
                                    "event_type",
                                    "concept_ref",
                                    "summary",
                                    "signal",
                                    "source_message_ids",
                                    "school_or_extended",
                                    "observed_student_outcome",
                                    "misconception_evidence",
                                ],
                            },
                        },
                    },
                    "required": ["version", "candidates"],
                },
                {"type": "null"},
            ]
        },
        "provisional_broad_subject": {
            "type": ["string", "null"],
            "enum": [*BROAD_SUBJECT_KEYS, None],
        },
        "workspace_intent": workspace_intent_output_schema(),
    },
    "required": ["text", "suggested_actions", "guided_check", "teaching_mode", "teaching_strategy", "teaching_method_id", "prior_method_relation", "segment_relation", "structured_segment_state", "parent_boundary", "candidate_metadata", "provisional_broad_subject", "workspace_intent"],
}


TUTOR_OUTPUT_RESPONSE_SCHEMA = {
    "name": TUTOR_TURN_SCHEMA_VERSION,
    "schema": TUTOR_OUTPUT_JSON_SCHEMA,
}
