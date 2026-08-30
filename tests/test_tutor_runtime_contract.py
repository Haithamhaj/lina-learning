"""Contract coverage for the production Tutor runtime policy boundary."""

from __future__ import annotations

import pytest

from services.tutor.candidate_events import TUTOR_OUTPUT_JSON_SCHEMA, TUTOR_OUTPUT_RESPONSE_SCHEMA
from services.tutor.runtime import (
    TUTOR_SHARED_INSTRUCTIONS,
    build_tutor_model_payload,
)
from services.tutor.teaching_decisions import PriorMethodRelation, TeachingMode, TeachingStrategy
from services.tutor.teaching_methods import ACTIVE_TEACHING_METHODS


def test_tutor_turn_v8_requires_optional_provisional_subject_without_rewriting_other_metadata() -> None:
    """SAFE-02 keeps one strict output contract for visible text and hidden decisions."""

    assert TUTOR_OUTPUT_RESPONSE_SCHEMA["name"] == "tutor_turn_v8"
    assert TUTOR_OUTPUT_JSON_SCHEMA["required"] == ["text", "suggested_actions", "guided_check", "teaching_mode", "teaching_strategy", "teaching_method_id", "prior_method_relation", "segment_relation", "structured_segment_state", "parent_boundary", "candidate_metadata", "provisional_broad_subject"]
    assert TUTOR_OUTPUT_JSON_SCHEMA["properties"]["provisional_broad_subject"] == {
        "type": ["string", "null"],
        "enum": [
            "MATH", "SCIENCE", "LANGUAGE_ARTS", "SOCIAL_STUDIES", "COMPUTING",
            "RELIGIOUS_STUDIES", "ARTS", "PHYSICAL_EDUCATION", "GENERAL_KNOWLEDGE",
            "OTHER", None,
        ],
    }
    assert TUTOR_OUTPUT_JSON_SCHEMA["properties"]["teaching_mode"] == {"type": ["string", "null"], "enum": [*(mode.value for mode in TeachingMode), None]}
    assert TUTOR_OUTPUT_JSON_SCHEMA["properties"]["teaching_strategy"] == {"type": ["string", "null"], "enum": [*(strategy.value for strategy in TeachingStrategy), None]}
    assert TUTOR_OUTPUT_JSON_SCHEMA["properties"]["teaching_method_id"] == {"type": ["string", "null"], "enum": [*(method.value for method in ACTIVE_TEACHING_METHODS), None]}
    assert TUTOR_OUTPUT_JSON_SCHEMA["properties"]["prior_method_relation"] == {"type": ["string", "null"], "enum": [*(relation.value for relation in PriorMethodRelation), None]}
    assert TUTOR_OUTPUT_JSON_SCHEMA["properties"]["segment_relation"] == {
        "type": ["string", "null"],
        "enum": ["CONTINUE", "NEW_SEGMENT", "UNCERTAIN", None],
    }
    state_schema = TUTOR_OUTPUT_JSON_SCHEMA["properties"]["structured_segment_state"]["anyOf"][0]
    assert state_schema["required"] == ["schema_version", "active_goal", "unresolved_point", "active_references", "established_facts", "source_message_ids"]
    assert state_schema["additionalProperties"] is False
    assert state_schema["properties"]["schema_version"]["enum"] == ["structured-segment-state-v1"]
    assert TUTOR_OUTPUT_JSON_SCHEMA["properties"]["suggested_actions"] == {
        "type": "array",
        "maxItems": 4,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "label": {"type": "string"},
                "kind": {"type": "string", "enum": ["NAVIGATION", "ANSWER_CHOICE"]},
            },
            "required": ["label", "kind"],
        },
    }
    assert TUTOR_OUTPUT_JSON_SCHEMA["properties"]["candidate_metadata"]["anyOf"][0]["properties"]["version"]["enum"] == ["candidate-event-v1"]
    parent_boundary = TUTOR_OUTPUT_JSON_SCHEMA["properties"]["parent_boundary"]
    assert parent_boundary["required"] == ["schema_version", "category", "applies", "model_action", "redirect"]
    assert parent_boundary["additionalProperties"] is False
    assert parent_boundary["properties"]["schema_version"]["enum"] == ["parent-boundary-v1"]
    assert parent_boundary["properties"]["category"]["enum"] == ["RELIGION", "SEXUAL_CONTENT", "RELATIONSHIPS", "POLITICS", "DEATH_GRIEF", "FAMILY_FINANCES", None]
    assert parent_boundary["properties"]["model_action"]["enum"] == ["ALLOW", "AGE_APPROPRIATE_ONLY", "REDIRECT_TO_PARENT"]


def test_candidate_contract_exposes_bounded_misconception_evidence_for_source_grounding() -> None:
    """CAND-01: the primary-call contract must ask Luna for auditable Student source grounding."""

    candidate_schema = TUTOR_OUTPUT_JSON_SCHEMA["properties"]["candidate_metadata"]["anyOf"][0]["properties"]["candidates"]["items"]
    evidence = candidate_schema["properties"]["misconception_evidence"]

    assert evidence == {
        "anyOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "version": {"type": "string", "enum": ["misconception-evidence-v1"]},
                    "incorrect_model": {"type": "string", "minLength": 1, "maxLength": 500},
                    "explicit_student_reasoning": {"type": "string", "minLength": 1, "maxLength": 500},
                    "source_message_id": {"type": "string"},
                },
                "required": ["version", "incorrect_model", "explicit_student_reasoning", "source_message_id"],
            },
            {"type": "null"},
        ],
    }


def test_candidate_contract_requires_nullable_misconception_evidence_for_strict_structured_outputs() -> None:
    """CAND-01: every Candidate property must be required; nullable means null is valid."""

    candidate_schema = TUTOR_OUTPUT_JSON_SCHEMA["properties"]["candidate_metadata"]["anyOf"][0]["properties"]["candidates"]["items"]

    assert set(candidate_schema["required"]) == set(candidate_schema["properties"])


def test_one_luna_call_receives_full_definitions_without_preselected_semantic_axes() -> None:
    payload = build_tutor_model_payload(question="Any literal phrase is only context for Luna.")

    assert "TeachingMode definitions" in str(payload["input"])
    assert "TeachingStrategy definitions" in str(payload["input"])
    assert "PriorMethodRelation definitions" in str(payload["input"])
    assert [method.value for method in ACTIVE_TEACHING_METHODS] == payload["active_teaching_methods"]
    assert "mode" not in payload
    assert "strategy" not in payload
    assert "eligible_teaching_methods" not in payload
    assert "Effective Parent Boundary settings" in str(payload["input"])
    assert "Parent Boundary semantic decision" in str(payload["input"])


def test_relation_guidance_distinguishes_a_new_topic_from_an_immediate_method_outcome() -> None:
    """A topic change must not be converted into method-effectiveness metadata."""

    payload = build_tutor_model_payload(question="A completely different topic now.")

    assert "A different topic is not DID_NOT_HELP" in str(payload["input"])
    assert "only when the selected method equals the immediate prior method" in str(payload["input"])


def test_tutor_instructions_require_calibrated_child_interaction_without_changing_evidence_authority() -> None:
    """Catches removal of the approved interaction, plain-text, or evidence boundaries from Tutor guidance."""

    instructions = TUTOR_SHARED_INSTRUCTIONS.casefold()
    for required_concept in (
        "approximately 10-year-old",
        "one concept or one or two small steps",
        "change representation or support",
        "zero to three emojis",
        "no markdown markers",
        "do not use latex",
        "suggested_actions",
        "label and kind",
        "normally provide two to four useful actions",
        "not proof of understanding or mastery",
        "source-linked observable learning signal",
        "confusion is not a misconception",
        "copy the supporting student reasoning span",
    ):
        assert required_concept in instructions


def test_language_switching_uses_current_turn_language_without_losing_recent_context() -> None:
    """Catches language switching that erases context or silently becomes a new learner/topic state."""

    payload = build_tutor_model_payload(
        question="Can I try another equivalent-fractions example?",
        recent_exchanges=[[
            {"message_id": "student-ar", "role": "student", "content": "ممكن تشرحي الكسور المتكافئة؟"},
            {"message_id": "tutor-ar", "role": "tutor", "content": "نعم، 1/2 = 2/4."},
        ]],
    )

    assert "Student question:\nCan I try another equivalent-fractions example?" in payload["input"]
    assert "ممكن تشرحي الكسور المتكافئة؟" in payload["input"]
    assert "فهمت الآن" not in payload["input"]
    assert "current message on every turn" in TUTOR_SHARED_INSTRUCTIONS
    assert "language switch" in TUTOR_SHARED_INSTRUCTIONS
    assert "separate learner profiles" in TUTOR_SHARED_INSTRUCTIONS
