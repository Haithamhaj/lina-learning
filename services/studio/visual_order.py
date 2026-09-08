"""Application-owned admission for bounded Tutor visual composition orders."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


VISUAL_ORDER_SCHEMA_VERSION = "workspace-visual-order-v1"
VISUAL_ORDER_V2_SCHEMA_VERSION = "workspace-visual-order-v2"
SEMANTIC_ALIGNMENT_SCHEMA_VERSION = "semantic-alignment-envelope-v1"
FROZEN_COMPOSITION_PACK_V1_SCHEMA_VERSION = "frozen-composition-pack-v1"
FROZEN_COMPOSITION_PACK_SCHEMA_VERSION = "frozen-composition-pack-v2"
VISUAL_LEARNER_CONTEXT_SCHEMA_VERSION = "visual-learner-context-v1"
_IMPLEMENTATION_CONTROL_PATTERNS = (
    re.compile(r"<\s*/?\s*(?:script|svg|html)\b", re.IGNORECASE),
    re.compile(r"\b(?:https?|javascript)\s*:", re.IGNORECASE),
    re.compile(r"\b(?:react|konva|jsxgraph|mathlive|renderer|css|html|svg|javascript)\b", re.IGNORECASE),
    re.compile(r"\b(?:import|function|const|let|var|class)\s+[A-Za-z_]", re.IGNORECASE),
)


def contains_implementation_control(value: str) -> bool:
    """Reject executable/rendering direction without rejecting educational words.

    Word boundaries intentionally distinguish the React framework from normal
    Science language such as reaction and reactants.
    """
    return any(pattern.search(value) is not None for pattern in _IMPLEMENTATION_CONTROL_PATTERNS)


class VisualOrderAdmissionError(ValueError):
    """The optional Tutor composition order is not safe to admit."""


class WorkspaceVisualOrder(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: Literal[VISUAL_ORDER_SCHEMA_VERSION]
    operation: Literal["COMPOSE"]
    pattern: Literal["PROCESS"]
    topology: Literal["SEQUENCE", "CYCLE"]
    objective: str = Field(min_length=1, max_length=500)
    required_semantics: list[str] = Field(min_length=2, max_length=8)
    required_relations: list[str] = Field(max_length=8)
    must_not_imply: list[str] = Field(max_length=6)
    source_references: list[str] = Field(max_length=6)
    personal_fact_keys: list[str] = Field(max_length=3)
    locale: str = Field(min_length=2, max_length=16)
    direction: Literal["ltr", "rtl", "auto"]
    use_display_name: bool

    @field_validator("required_semantics", "required_relations", "must_not_imply", "source_references", "personal_fact_keys")
    @classmethod
    def values_are_unique_and_nonempty(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values) or len({value.casefold() for value in values}) != len(values):
            raise ValueError("Visual order values must be non-empty and unique.")
        return values

    @model_validator(mode="after")
    def educational_text_has_no_implementation_control(self) -> "WorkspaceVisualOrder":
        values = [self.objective, *self.required_semantics, *self.required_relations, *self.must_not_imply]
        if any(contains_implementation_control(value) for value in values):
            raise ValueError("Visual order must contain educational meaning only.")
        return self


class WorkspaceVisualOrderV2(BaseModel):
    """Small semantic order union for the four production Canvas patterns."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: Literal[VISUAL_ORDER_V2_SCHEMA_VERSION]
    operation: Literal["COMPOSE"]
    pattern: Literal["PROCESS", "SPATIAL_MANIPULATION", "MATH_VISUALIZATION", "MATH_INPUT"]
    topology: Literal["SEQUENCE", "CYCLE"] | None
    interaction_goal: Literal["EXPLAIN_PROCESS", "PLACE_OBJECT", "CONSTRUCT_POINT", "AUTHOR_EXPRESSION"]
    objective: str = Field(min_length=1, max_length=500)
    required_semantics: list[str] = Field(min_length=2, max_length=8)
    required_relations: list[str] = Field(max_length=8)
    must_not_imply: list[str] = Field(max_length=6)
    source_references: list[str] = Field(max_length=6)
    personal_fact_keys: list[str] = Field(max_length=3)
    locale: str = Field(min_length=2, max_length=16)
    direction: Literal["ltr", "rtl", "auto"]
    use_display_name: bool

    @field_validator("required_semantics", "required_relations", "must_not_imply", "source_references", "personal_fact_keys")
    @classmethod
    def values_are_unique_and_nonempty(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values) or len({value.casefold() for value in values}) != len(values):
            raise ValueError("Visual order values must be non-empty and unique.")
        return values

    @model_validator(mode="after")
    def pattern_matches_goal(self) -> "WorkspaceVisualOrderV2":
        expected = {
            "PROCESS": "EXPLAIN_PROCESS",
            "SPATIAL_MANIPULATION": "PLACE_OBJECT",
            "MATH_VISUALIZATION": "CONSTRUCT_POINT",
            "MATH_INPUT": "AUTHOR_EXPRESSION",
        }
        if self.interaction_goal != expected[self.pattern]:
            raise ValueError("Visual pattern and semantic interaction goal do not match.")
        if (self.pattern == "PROCESS") != (self.topology is not None):
            raise ValueError("Only Process orders have topology.")
        values = [self.objective, *self.required_semantics, *self.required_relations, *self.must_not_imply]
        if any(contains_implementation_control(value) for value in values):
            raise ValueError("Visual order must contain educational meaning only.")
        return self


@dataclass(frozen=True)
class AdmittedVisualOrder:
    admitted_order: dict[str, object]
    semantic_alignment: dict[str, object]
    frozen_composition_pack: dict[str, object]
    order_digest: str


def visual_order_output_schema() -> dict[str, object]:
    v1 = {"type": "object", "additionalProperties": False, "properties": {
        "version": {"type": "string", "enum": [VISUAL_ORDER_SCHEMA_VERSION]},
        "operation": {"type": "string", "enum": ["COMPOSE"]},
        "pattern": {"type": "string", "enum": ["PROCESS"]},
        "topology": {"type": "string", "enum": ["SEQUENCE", "CYCLE"]},
        "objective": {"type": "string", "minLength": 1, "maxLength": 500},
        "required_semantics": {"type": "array", "minItems": 2, "maxItems": 8, "items": {"type": "string", "minLength": 1, "maxLength": 500}},
        "required_relations": {"type": "array", "maxItems": 8, "items": {"type": "string", "minLength": 1, "maxLength": 500}},
        "must_not_imply": {"type": "array", "maxItems": 6, "items": {"type": "string", "minLength": 1, "maxLength": 500}},
        "source_references": {"type": "array", "maxItems": 6, "items": {"type": "string", "minLength": 1, "maxLength": 256}},
        "personal_fact_keys": {"type": "array", "maxItems": 3, "items": {"type": "string", "minLength": 1, "maxLength": 128}},
        "locale": {"type": "string", "minLength": 2, "maxLength": 16},
        "direction": {"type": "string", "enum": ["ltr", "rtl", "auto"]},
        "use_display_name": {"type": "boolean"},
    }, "required": ["version", "operation", "pattern", "topology", "objective", "required_semantics", "required_relations", "must_not_imply", "source_references", "personal_fact_keys", "locale", "direction", "use_display_name"]}
    v2 = {"type": "object", "additionalProperties": False, "properties": {
        **v1["properties"],
        "version": {"type": "string", "enum": [VISUAL_ORDER_V2_SCHEMA_VERSION]},
        "pattern": {"type": "string", "enum": ["PROCESS", "SPATIAL_MANIPULATION", "MATH_VISUALIZATION", "MATH_INPUT"]},
        "topology": {"anyOf": [{"type": "string", "enum": ["SEQUENCE", "CYCLE"]}, {"type": "null"}]},
        "interaction_goal": {"type": "string", "enum": ["EXPLAIN_PROCESS", "PLACE_OBJECT", "CONSTRUCT_POINT", "AUTHOR_EXPRESSION"]},
    }, "required": [*v1["required"], "interaction_goal"]}
    return {"anyOf": [v1, v2, {"type": "null"}]}


def admit_visual_order(
    raw_order: object,
    *,
    authorized_source_references: dict[str, dict[str, object]],
    visual_personalization_catalog: dict[str, dict[str, object]],
    core_profile: dict[str, object],
) -> AdmittedVisualOrder:
    try:
        model = WorkspaceVisualOrderV2 if isinstance(raw_order, dict) and raw_order.get("version") == VISUAL_ORDER_V2_SCHEMA_VERSION else WorkspaceVisualOrder
        order = model.model_validate(raw_order)
    except ValidationError as error:
        raise VisualOrderAdmissionError("VISUAL_ORDER_INVALID") from error
    if not set(order.source_references).issubset(authorized_source_references):
        raise VisualOrderAdmissionError("SOURCE_REFERENCE_UNAUTHORIZED")
    if not set(order.personal_fact_keys).issubset(visual_personalization_catalog):
        raise VisualOrderAdmissionError("PERSONAL_FACT_UNAUTHORIZED")
    alignment = {
        "version": SEMANTIC_ALIGNMENT_SCHEMA_VERSION,
        "objective": order.objective,
        "required_semantics": [{"id": f"F{index}", "statement": statement} for index, statement in enumerate(order.required_semantics, 1)],
        "required_relations": [{"id": f"R{index}", "statement": statement} for index, statement in enumerate(order.required_relations, 1)],
        "must_not_imply": order.must_not_imply,
    }
    excerpts = [{"source_ref": reference, "text": authorized_source_references[reference].get("text", "")} for reference in order.source_references]
    selected_facts = [{"fact_key": key, "category": visual_personalization_catalog[key]["category"], "display_statement": visual_personalization_catalog[key]["display_statement"]} for key in order.personal_fact_keys]
    selected_profile = {key: core_profile[key] for key in ("age_years", "grade_level") if core_profile.get(key) is not None}
    if order.use_display_name and core_profile.get("display_name"):
        selected_profile["display_name"] = core_profile["display_name"]
    learner_context = {"version": VISUAL_LEARNER_CONTEXT_SCHEMA_VERSION, "core_profile": selected_profile, "selected_personal_facts": selected_facts}
    grounding = {"origin": "RETRIEVED_SOURCE", "excerpts": excerpts} if excerpts else {"origin": "ADMITTED_TUTOR_ORDER", "excerpts": []}
    admitted_order = order.model_dump(mode="json")
    if order.pattern == "PROCESS":
        motion = ["REVEAL_IN_ORDER", "TRACE_SEQUENCE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"] if order.topology == "SEQUENCE" else ["REVEAL_IN_ORDER", "TRACE_CYCLE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"]
        pack: dict[str, object] = {"version": FROZEN_COMPOSITION_PACK_SCHEMA_VERSION, "admitted_order": admitted_order, "semantic_alignment": alignment, "pattern": order.pattern, "topology": order.topology, "locale": order.locale, "direction": order.direction, "grounding": grounding, "visual_learner_context": learner_context, "capability_pack": {"identity": "process-capability-pack-v2", "process_stage_limit": [2, 8]}, "allowed_motion_intents": motion, "allowed_affordances": ["FOCUS_OBJECT", "DEEMPHASIZE_OTHERS", "REVEAL_OBJECT_DETAIL", "TRACE_RELATION", "TRANSITION_FOCUS"], "allowed_art_handles": ["egg", "larva", "pupa", "butterfly", "drop", "filter", "vessel", "idea", "draft", "review"]}
    else:
        capabilities = {
            "SPATIAL_MANIPULATION": {"identity": "canvas-spatial-capability-pack-v1", "object_count_limit": [1, 1], "target_count_limit": [1, 1], "allowed_relations": ["INSIDE", "MATCH", "GROUP"], "allowed_interactions": ["PLACE_OBJECT"], "label_max_length": 40},
            "MATH_VISUALIZATION": {"identity": "canvas-math-visualization-capability-pack-v1", "construction_family": "CARTESIAN_POINT", "coordinate_bounds": [-4, 4], "point_count_limit": [1, 1], "allowed_interactions": ["PLACE_POINT", "SUBMIT_CONSTRUCTION"], "label_max_length": 24},
            "MATH_INPUT": {"identity": "canvas-math-input-capability-pack-v1", "input_representation": "LATEX", "expression_max_length": 120, "allowed_interactions": ["SUBMIT_EXPRESSION"]},
        }
        capability = capabilities[order.pattern]
        pack = {"version": "frozen-composition-pack-v3", "admitted_order": admitted_order, "semantic_alignment": alignment, "pattern": order.pattern, "topology": None, "locale": order.locale, "direction": order.direction, "grounding": grounding, "visual_learner_context": learner_context, "capability_pack": capability, "allowed_affordances": capability["allowed_interactions"]}
    digest = sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return AdmittedVisualOrder(admitted_order=admitted_order, semantic_alignment=alignment, frozen_composition_pack=pack, order_digest=digest)
