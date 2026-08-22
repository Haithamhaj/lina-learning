"""Versioned, source-linked Candidate Event contract for one Tutor turn."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


CANDIDATE_EVENT_SCHEMA_VERSION = "candidate-event-v1"
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
    "current_focus_signal",
    "extended_learning_event",
]


class CandidateEventContractError(ValueError):
    """The Tutor's hidden Candidate Event metadata is not safe to persist."""


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
    for candidate in metadata.candidates:
        source_ids = set(candidate.source_message_ids)
        if not source_ids.issubset(allowed_source_message_ids):
            raise CandidateEventContractError("Candidate metadata references an unavailable raw message.")
    return metadata


TUTOR_OUTPUT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "text": {"type": "string"},
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
                                    "concept_ref": {"type": ["string", "null"]},
                                    "summary": {"type": "string"},
                                    "signal": {"type": "string"},
                                    "source_message_ids": {"type": "array", "items": {"type": "string"}},
                                    "school_or_extended": {"type": "string", "enum": ["school", "extended"]},
                                    "observed_student_outcome": {"type": ["string", "null"]},
                                },
                                "required": [
                                    "event_type",
                                    "concept_ref",
                                    "summary",
                                    "signal",
                                    "source_message_ids",
                                    "school_or_extended",
                                    "observed_student_outcome",
                                ],
                            },
                        },
                    },
                    "required": ["version", "candidates"],
                },
                {"type": "null"},
            ]
        },
    },
    "required": ["text", "candidate_metadata"],
}


TUTOR_OUTPUT_RESPONSE_SCHEMA = {
    "name": "tutor_turn_v1",
    "schema": TUTOR_OUTPUT_JSON_SCHEMA,
}
