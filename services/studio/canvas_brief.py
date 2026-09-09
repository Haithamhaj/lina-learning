"""Strict educational handoff from the Primary Tutor to Canvas composition."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


CANVAS_BRIEF_VERSION = "canvas-brief-v1"
_IMPLEMENTATION_CONTROL = re.compile(
    r"\b(?:jsxgraph|konva|mathlive|renderer|component|provider|javascript|typescript|jsx|css|svg)\b",
    re.IGNORECASE,
)


class CanvasBriefContractError(ValueError):
    """Raised when untrusted Tutor output is not an educational Canvas brief."""


class CanvasQuantityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    value: str = Field(min_length=1, max_length=120)
    unit: str | None = Field(..., min_length=1, max_length=64)


class CanvasRelationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    source_id: str = Field(min_length=1, max_length=64)
    target_id: str = Field(min_length=1, max_length=64)
    meaning: str = Field(min_length=1, max_length=240)


class CanvasBriefV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: Literal[CANVAS_BRIEF_VERSION]
    subject_key: str = Field(min_length=1, max_length=64)
    objective: str = Field(min_length=1, max_length=500)
    student_request: str = Field(min_length=1, max_length=500)
    requested_representation: str | None = Field(..., min_length=1, max_length=120)
    facts: list[str] = Field(..., max_length=12)
    relations: list[CanvasRelationV1] = Field(..., max_length=12)
    quantities: list[CanvasQuantityV1] = Field(..., max_length=12)
    desired_student_action: str | None = Field(..., min_length=1, max_length=240)
    must_not_imply: list[str] = Field(..., max_length=12)
    source_references: list[str] = Field(..., max_length=6)
    locale: str = Field(min_length=2, max_length=16)
    direction: Literal["ltr", "rtl", "auto"]

    @field_validator("objective", "student_request", "requested_representation", "desired_student_action", "facts", "must_not_imply")
    @classmethod
    def educational_text_has_no_implementation_control(cls, value: str | list[str] | None):
        values = value if isinstance(value, list) else [value]
        if any(item is not None and _IMPLEMENTATION_CONTROL.search(item) for item in values):
            raise ValueError("Canvas brief must not contain implementation control.")
        return value


def parse_canvas_brief(payload: object) -> CanvasBriefV1 | None:
    if payload is None:
        return None
    try:
        return CanvasBriefV1.model_validate(payload)
    except ValidationError as error:
        raise CanvasBriefContractError("Canvas brief violates the contract.") from error


def audit_canvas_brief(
    payload: object,
    *,
    allowed_source_references: set[str],
    safety_allows: bool,
) -> dict[str, object]:
    """Validate a Tutor handoff before it can schedule composition work."""
    if payload is None or not safety_allows:
        return {"status": "NOT_REQUESTED", "reason_code": None, "brief": None, "brief_digest": None}
    try:
        brief = parse_canvas_brief(payload)
    except CanvasBriefContractError:
        return {"status": "REJECTED", "reason_code": "CANVAS_BRIEF_INVALID", "brief": None, "brief_digest": None}
    if brief is None:
        return {"status": "NOT_REQUESTED", "reason_code": None, "brief": None, "brief_digest": None}
    if not set(brief.source_references).issubset(allowed_source_references):
        return {"status": "REJECTED", "reason_code": "CANVAS_BRIEF_SOURCE_UNAUTHORIZED", "brief": None, "brief_digest": None}
    serialized = brief.model_dump(mode="json")
    digest = sha256(json.dumps(serialized, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return {"status": "ADMITTED", "reason_code": None, "brief": serialized, "brief_digest": digest}


def canvas_brief_output_schema() -> dict[str, object]:
    schema = CanvasBriefV1.model_json_schema()
    definitions = schema.pop("$defs", {})

    def inline(value: object) -> object:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                return inline(deepcopy(definitions[reference.removeprefix("#/$defs/")]))
            return {key: inline(item) for key, item in value.items()}
        if isinstance(value, list):
            return [inline(item) for item in value]
        return value

    return {"anyOf": [inline(schema), {"type": "null"}]}
