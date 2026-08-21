"""Contract coverage for the production Tutor runtime policy boundary."""

from __future__ import annotations

import pytest

from services.tutor.runtime import TeachingMode, TeachingStrategy, infer_tutor_mode, select_teaching_strategy


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
