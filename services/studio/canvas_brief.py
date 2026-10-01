"""Strict educational handoff from the Primary Tutor to Canvas composition."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_serializer


CANVAS_BRIEF_VERSION = "canvas-brief-v1"
LEARNER_EXPERIENCES = (
    "OBSERVE", "COMPARE", "EXPLORE", "MANIPULATE", "CONSTRUCT",
    "SEQUENCE", "CLASSIFY", "PRACTICE", "ANSWER", "EXPLAIN",
)
_LEARNER_EXPERIENCE_ACTION = {
    "OBSERVE": "Observe the relevant relationship or change.",
    "COMPARE": "Compare the relevant states, quantities, or outcomes.",
    "EXPLORE": "Explore how the relevant relationship changes.",
    "MANIPULATE": "Manipulate the relevant state directly and observe the effect.",
    "CONSTRUCT": "Construct or assemble the relevant elements.",
    "SEQUENCE": "Arrange the relevant elements into a meaningful sequence.",
    "CLASSIFY": "Classify the relevant elements by their roles or properties.",
    "PRACTICE": "Practice the target idea through a meaningful attempt.",
    "ANSWER": "Answer the target question using the visual context.",
    "EXPLAIN": "Explain the relevant relationship using what is shown.",
}
VISUAL_CONTEXT_SELECTION_VERSION = "canvas-visual-context-selection-v1"
VISUAL_LEARNER_CONTEXT_VERSION = "visual-learner-context-v1"
PERSONAL_FACT_IDENTITY_MAX_LENGTH = 128
_PERSONAL_FACT_IDENTITY = re.compile(
    rf"^[a-z][a-z0-9_-]*(?:[.:][a-z][a-z0-9_-]*)*$"
)
_IMPLEMENTATION_CONTROL = re.compile(
    r"\b(?:jsxgraph|konva|mathlive|renderer|component|provider|javascript|typescript|jsx|css|svg)\b",
    re.IGNORECASE,
)


class CanvasBriefContractError(ValueError):
    """Raised when untrusted Tutor output is not an educational Canvas brief."""


class CanvasVisualContextSelectionV1(BaseModel):
    """Same-Tutor-call selection of already-filtered facts, never free-form memory."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[VISUAL_CONTEXT_SELECTION_VERSION]
    personal_fact_keys: list[str] = Field(..., max_length=3)

    @field_validator("personal_fact_keys")
    @classmethod
    def unique_fact_keys(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)) or any(
            len(key) > PERSONAL_FACT_IDENTITY_MAX_LENGTH
            or _PERSONAL_FACT_IDENTITY.fullmatch(key) is None
            for key in value
        ):
            raise ValueError("Visual context selection must contain unique exact fact keys")
        return value


class VisualLearnerCoreProfileV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age_years: int | None = Field(default=None, ge=3, le=25)
    grade_level: str | None = Field(default=None, min_length=1, max_length=32)


class VisualLearnerFactV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    fact_key: str = Field(min_length=1, max_length=PERSONAL_FACT_IDENTITY_MAX_LENGTH, pattern=_PERSONAL_FACT_IDENTITY.pattern)
    category: Literal["PREFERENCE", "FAVORITE", "ACTIVITY", "PET"]
    display_statement: str = Field(min_length=1, max_length=300)


class VisualLearnerIntelligenceV1(BaseModel):
    """One already-authorized Learning Intelligence item selected only as visual support."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source_kind: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=600)
    concept_ref: str | None = Field(default=None, min_length=1, max_length=128)


class VisualLearnerContextV1(BaseModel):
    """Bounded learner calibration and optional memory support for Canvas."""

    model_config = ConfigDict(extra="forbid")
    version: Literal[VISUAL_LEARNER_CONTEXT_VERSION]
    core_profile: VisualLearnerCoreProfileV1
    selected_personal_facts: list[VisualLearnerFactV1] = Field(default_factory=list, max_length=3)
    selected_learning_intelligence: list[VisualLearnerIntelligenceV1] = Field(default_factory=list, max_length=3)

    @model_serializer(mode="wrap")
    def serialize_context(self, handler):
        data = handler(self)
        if not self.selected_learning_intelligence:
            data.pop("selected_learning_intelligence", None)
        return data


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
    student_request: str = Field(min_length=1, max_length=4000)
    relevant_conversation: str | None = Field(default=None, min_length=1, max_length=300)
    # Legacy persisted briefs may still carry these two fields. New Tutor output
    # does not own either representation choice or negative teaching constraints.
    requested_representation: str | None = Field(default=None, min_length=1, max_length=120)
    facts: list[str] = Field(..., max_length=12)
    relations: list[CanvasRelationV1] = Field(..., max_length=12)
    quantities: list[CanvasQuantityV1] = Field(..., max_length=12)
    desired_student_action: str | None = Field(..., min_length=1, max_length=240)
    must_not_imply: list[str] = Field(default_factory=list, max_length=12)
    source_references: list[str] = Field(..., max_length=6)
    locale: str = Field(min_length=2, max_length=16)
    direction: Literal["ltr", "rtl", "auto"]

    @model_serializer(mode="wrap")
    def serialize_brief(self, handler):
        data = handler(self)
        if self.relevant_conversation is None:
            data.pop("relevant_conversation", None)
        # Preserve exact historical serialization when legacy fields were
        # supplied, while keeping them out of newly server-bound handoffs.
        if "requested_representation" not in self.model_fields_set:
            data.pop("requested_representation", None)
        if "must_not_imply" not in self.model_fields_set:
            data.pop("must_not_imply", None)
        return data

    @field_validator("objective", "student_request", "relevant_conversation", "requested_representation", "desired_student_action", "facts", "must_not_imply")
    @classmethod
    def educational_text_has_no_implementation_control(cls, value: str | list[str] | None):
        values = value if isinstance(value, list) else [value]
        if any(item is not None and _IMPLEMENTATION_CONTROL.search(item) for item in values):
            raise ValueError("Canvas brief must not contain implementation control.")
        return value


def bind_tutor_canvas_brief(
    payload: object,
    *,
    student_request: str,
    authorized_source_references: tuple[str, ...] | list[str] = (),
) -> object:
    """Bind application-owned request identity and authorized source lineage.

    The Primary Tutor owns educational meaning only. Student/request identity,
    source-reference identity and authorization are application-owned.
    """
    if payload is None or not isinstance(payload, dict):
        return payload
    bound = dict(payload)
    bound["student_request"] = student_request
    bound["source_references"] = list(dict.fromkeys(authorized_source_references))
    experiences = bound.pop("learner_experience", None)
    if isinstance(experiences, list) and experiences:
        normalized = [
            _LEARNER_EXPERIENCE_ACTION[item]
            for item in experiences
            if isinstance(item, str) and item in _LEARNER_EXPERIENCE_ACTION
        ]
        bound["desired_student_action"] = " ".join(dict.fromkeys(normalized)) or None
    bound.pop("requested_representation", None)
    bound.pop("must_not_imply", None)
    return bound


def parse_canvas_brief(payload: object) -> CanvasBriefV1 | None:
    if payload is None:
        return None
    try:
        return CanvasBriefV1.model_validate(payload)
    except ValidationError as error:
        raise CanvasBriefContractError("Canvas brief violates the contract.") from error


def visual_context_selection_output_schema() -> dict[str, object]:
    schema = CanvasVisualContextSelectionV1.model_json_schema()
    return {"anyOf": [schema, {"type": "null"}]}


def resolve_visual_memory_context(
    *,
    selected_keys: list[str] | tuple[str, ...],
    memory_catalog: dict[str, dict[str, object]],
    core_profile: dict[str, object],
) -> VisualLearnerContextV1:
    """Resolve JEV-selected optional memory support without flattening authority."""

    keys = list(selected_keys)
    if len(keys) > 3 or len(keys) != len(set(keys)) or not set(keys).issubset(memory_catalog):
        raise CanvasBriefContractError("Visual memory support selection is outside the bounded catalogue.")

    personal_facts: list[dict[str, object]] = []
    learning_intelligence: list[dict[str, object]] = []
    for key in keys:
        item = memory_catalog[key]
        layer = item.get("memory_layer")
        if layer == "PERSONAL_FACT":
            personal_facts.append({
                "fact_key": item.get("fact_key"),
                "category": item.get("kind"),
                "display_statement": item.get("text"),
            })
        elif layer == "LEARNING_INTELLIGENCE":
            learning_intelligence.append({
                "source_kind": item.get("kind"),
                "text": item.get("text"),
                "concept_ref": item.get("concept_ref"),
            })
        else:
            raise CanvasBriefContractError("Visual memory support layer is not authorized.")

    return VisualLearnerContextV1.model_validate({
        "version": VISUAL_LEARNER_CONTEXT_VERSION,
        "core_profile": {
            "age_years": core_profile.get("age_years"),
            "grade_level": None if core_profile.get("grade_level") is None else str(core_profile["grade_level"]),
        },
        "selected_personal_facts": personal_facts,
        "selected_learning_intelligence": learning_intelligence,
    })


def resolve_visual_learner_context(
    payload: object,
    *,
    visual_personalization_catalog: dict[str, dict[str, str]],
    core_profile: dict[str, object],
) -> VisualLearnerContextV1:
    """Resolve exact safe keys against the established server-owned catalogue."""
    selection = CanvasVisualContextSelectionV1.model_validate(payload) if payload is not None else None
    selected = [] if selection is None else [
        {"fact_key": key, **visual_personalization_catalog[key]}
        for key in selection.personal_fact_keys
        if key in visual_personalization_catalog
    ]
    if selection is not None and len(selected) != len(selection.personal_fact_keys):
        raise CanvasBriefContractError("Canvas visual context selection is outside the filtered catalogue.")
    return VisualLearnerContextV1.model_validate({
        "version": VISUAL_LEARNER_CONTEXT_VERSION,
        "core_profile": {"age_years": core_profile.get("age_years"), "grade_level": None if core_profile.get("grade_level") is None else str(core_profile["grade_level"])},
        "selected_personal_facts": selected,
    })


def audit_canvas_brief(
    payload: object,
    *,
    allowed_source_references: set[str],
    safety_allows: bool,
    visual_context_selection: object = None,
    visual_personalization_catalog: dict[str, dict[str, str]] | None = None,
    core_profile: dict[str, object] | None = None,
    visual_learner_context: object | None = None,
) -> dict[str, object]:
    """Validate a Tutor handoff before it can schedule composition work."""
    if payload is None or not safety_allows:
        return {"status": "NOT_REQUESTED", "reason_code": None, "brief": None, "brief_digest": None, "visual_learner_context": None}
    try:
        brief = parse_canvas_brief(payload)
    except CanvasBriefContractError:
        return {"status": "REJECTED", "reason_code": "CANVAS_BRIEF_INVALID", "brief": None, "brief_digest": None, "visual_learner_context": None}
    if brief is None:
        return {"status": "NOT_REQUESTED", "reason_code": None, "brief": None, "brief_digest": None, "visual_learner_context": None}
    if not set(brief.source_references).issubset(allowed_source_references):
        return {"status": "REJECTED", "reason_code": "CANVAS_BRIEF_SOURCE_UNAUTHORIZED", "brief": None, "brief_digest": None, "visual_learner_context": None}
    try:
        visual_context = (
            VisualLearnerContextV1.model_validate(visual_learner_context)
            if visual_learner_context is not None
            else resolve_visual_learner_context(
                visual_context_selection,
                visual_personalization_catalog=visual_personalization_catalog or {},
                core_profile=core_profile or {},
            )
        )
    except (ValidationError, CanvasBriefContractError):
        return {"status": "REJECTED", "reason_code": "CANVAS_VISUAL_CONTEXT_INVALID", "brief": None, "brief_digest": None, "visual_learner_context": None}
    serialized = brief.model_dump(mode="json")
    digest = sha256(json.dumps(serialized, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return {"status": "ADMITTED", "reason_code": None, "brief": serialized, "brief_digest": digest, "visual_learner_context": visual_context.model_dump(mode="json")}


def canvas_brief_output_schema() -> dict[str, object]:
    schema = CanvasBriefV1.model_json_schema()
    # The Primary Tutor emits educational intent and grounding only. The
    # application binds the exact current Student request; the visual teacher
    # owns representation choice. Legacy persisted fields remain readable by
    # CanvasBriefV1 but are not part of new Tutor model output.
    for server_or_canvas_owned in (
        "student_request",
        "requested_representation",
        "must_not_imply",
        "source_references",
        "desired_student_action",
    ):
        schema["properties"].pop(server_or_canvas_owned, None)
        if server_or_canvas_owned in schema["required"]:
            schema["required"].remove(server_or_canvas_owned)
    schema["required"].append("relevant_conversation")
    schema["properties"]["relevant_conversation"].pop("default", None)
    schema["properties"]["learner_experience"] = {
        "type": "array",
        "minItems": 1,
        "maxItems": 3,
        "items": {"type": "string", "enum": list(LEARNER_EXPERIENCES)},
        "description": (
            "Bounded learner experience only; describe what the learner should do, "
            "never the visual form, object layout, renderer, tool, or implementation."
        ),
    }
    schema["required"].append("learner_experience")
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
