"""Contract coverage for the production Tutor runtime policy boundary."""

from __future__ import annotations

import pytest

from services.tutor.candidate_events import TUTOR_OUTPUT_JSON_SCHEMA, TUTOR_OUTPUT_RESPONSE_SCHEMA
from services.tutor.runtime import (
    TUTOR_SHARED_INSTRUCTIONS,
    TeachingMode,
    TeachingStrategy,
    build_tutor_model_payload,
    infer_tutor_mode,
    select_teaching_strategy,
)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Explain equivalent fractions.", TeachingMode.LEARN),
        ("Why do equivalent fractions have the same value?", TeachingMode.LEARN),
        ("كيف تعمل الكسور المتكافئة؟", TeachingMode.LEARN),
        ("Help me with my homework worksheet, but do not tell me the answer yet.", TeachingMode.HOMEWORK),
        ("I am curious about black holes outside our school topic.", TeachingMode.EXPLORE),
        ("Can we review decimals again?", TeachingMode.REVIEW),
        ("Quiz me on multiplying by 10.", TeachingMode.QUIZ),
        ("ساعدني في واجبي بدون الحل مباشرة.", TeachingMode.HOMEWORK),
        ("اختبرني في الكسور.", TeachingMode.QUIZ),
    ],
)
def test_mode_inference_selects_a_runtime_mode_from_the_current_message(
    question: str,
    expected: TeachingMode,
) -> None:
    assert infer_tutor_mode(question) is expected


def test_genuinely_stuck_message_requires_explanation_then_a_new_check() -> None:
    assert select_teaching_strategy("I am genuinely stuck and do not understand this.") is TeachingStrategy.EXPLAIN_THEN_CHECK


def test_current_independence_does_not_force_historical_support_strategy() -> None:
    assert select_teaching_strategy("I solved it myself: 4.5 × 10 = 45.") is TeachingStrategy.INDEPENDENT_CHECK


def test_tutor_turn_v4_requires_a_nullable_method_without_changing_candidate_metadata() -> None:
    """Catches a structured-output upgrade that omits actions or rewrites Candidate metadata."""

    assert TUTOR_OUTPUT_RESPONSE_SCHEMA["name"] == "tutor_turn_v4"
    assert TUTOR_OUTPUT_JSON_SCHEMA["required"] == ["text", "suggested_actions", "candidate_metadata", "teaching_method_id"]
    assert TUTOR_OUTPUT_JSON_SCHEMA["properties"]["teaching_method_id"] == {
        "type": ["string", "null"],
    }
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


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("فهمت", TeachingStrategy.INDEPENDENT_CHECK),
        ("تمام فهمت", TeachingStrategy.INDEPENDENT_CHECK),
        ("I understand", TeachingStrategy.INDEPENDENT_CHECK),
        ("Got it", TeachingStrategy.INDEPENDENT_CHECK),
        ("مش فاهمة", TeachingStrategy.EXPLAIN_THEN_CHECK),
        ("لسه مش واضحة", TeachingStrategy.EXPLAIN_THEN_CHECK),
        ("I don't understand", TeachingStrategy.EXPLAIN_THEN_CHECK),
        ("Still not clear", TeachingStrategy.EXPLAIN_THEN_CHECK),
    ],
)
def test_bilingual_interaction_intents_select_existing_teaching_strategies(
    message: str, expected: TeachingStrategy,
) -> None:
    """Catches self-reports or confusion bypassing the existing adaptive strategy routing."""

    assert select_teaching_strategy(message) is expected


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
    ):
        assert required_concept in instructions


def test_language_switching_uses_current_turn_language_without_losing_recent_context() -> None:
    """Catches language switching that erases context or silently becomes a new learner/topic state."""

    payload = build_tutor_model_payload(
        question="Can I try another equivalent-fractions example?",
        session_messages=[
            {"role": "student", "content": "ممكن تشرحي الكسور المتكافئة؟"},
            {"role": "tutor", "content": "نعم، 1/2 = 2/4."},
            {"role": "student", "content": "فهمت الآن"},
        ],
    )

    assert "Student question:\nCan I try another equivalent-fractions example?" in payload["input"]
    assert "ممكن تشرحي الكسور المتكافئة؟" in payload["input"]
    assert "فهمت الآن" in payload["input"]
    assert "current message on every turn" in TUTOR_SHARED_INSTRUCTIONS
    assert "language switch" in TUTOR_SHARED_INSTRUCTIONS
    assert "separate learner profiles" in TUTOR_SHARED_INSTRUCTIONS
