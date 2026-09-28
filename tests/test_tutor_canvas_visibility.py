"""Bounded wording checks from synthetic Golden visual-delivery patterns."""

from __future__ import annotations

import pytest

from services.tutor.canvas_visibility import ensure_new_canvas_is_not_claimed_visible


@pytest.mark.parametrize(
    "text",
    [
        "الجذور تحت التربة، والساق فوقها. انظري إلى الرسم لترَي ترتيب الأجزاء.",
        "انظري إلى ترتيب الأجزاء في الرسم: الجذور تحت التربة، والساق فوقها.",
        "أعددتُ لكِ رسماً يوضح الأجزاء. أي جزء يوجد تحت التربة؟",
        "The roots grow below the soil. Look at the drawing to see where they are.",
        "I prepared a diagram. Which part grows below the soil?",
        "الصورة ظاهرة أمامك. أين الجذور؟",
        "هذه صورة توضح الجذور. أين الجذور؟",
        "The diagram is ready. Which part is below the soil?",
    ],
)
def test_new_canvas_request_repairs_premature_visibility_but_keeps_teaching(text: str) -> None:
    repaired, changed = ensure_new_canvas_is_not_claimed_visible(text, new_composition_requested=True)
    assert changed
    assert any(phrase in repaired for phrase in (
        "الجذور تحت التربة", "أي جزء يوجد تحت التربة", "أين الجذور", "roots grow below the soil", "part grows below", "part is below",
    ))
    assert "انظري إلى" not in repaired
    assert "أعددتُ" not in repaired
    assert "Look at the drawing" not in repaired
    assert "I prepared" not in repaired
    assert "أجهّز" in repaired or "I’m preparing" in repaired


@pytest.mark.parametrize(
    "text",
    [
        "الجذور تحت التربة. أجهّز لكِ رسماً يوضحها.",
        "The roots grow below the soil. I’m preparing a diagram to show them.",
        "I’m drawing a diagram to show the plant parts.",
        "سأرسم لكِ صورة توضّح أجزاء النبتة.",
        "When the visual is ready, we can use it together.",
        "عندما يصبح الرسم جاهزًا، نستخدمه معًا.",
    ],
)
def test_new_canvas_request_keeps_truthful_preparation_unchanged(text: str) -> None:
    assert ensure_new_canvas_is_not_claimed_visible(text, new_composition_requested=True) == (text, False)


def test_existing_ready_canvas_reference_is_allowed_without_new_request() -> None:
    text = "Look at the drawing in Canvas and compare the two parts."
    assert ensure_new_canvas_is_not_claimed_visible(text, new_composition_requested=False) == (text, False)


def test_non_canvas_turn_is_unchanged() -> None:
    text = "انظري إلى كلمة «رسمت» في الجملة، ثم حددي الفاعل."
    assert ensure_new_canvas_is_not_claimed_visible(text, new_composition_requested=False) == (text, False)


def test_repaired_clause_does_not_leave_a_comma_before_preparation() -> None:
    text = "The roots grow below the soil, so look at the drawing to see where they are."
    repaired, changed = ensure_new_canvas_is_not_claimed_visible(text, new_composition_requested=True)
    assert changed
    assert repaired.startswith("The roots grow below the soil. I’m preparing")


def test_new_visual_repair_preserves_ordinary_gas_form_and_equal_shape_explanations() -> None:
    science = (
        "بخار الماء ماءٌ في صورة غاز، وجزيئاته متباعدة وتتحرك. "
        "انظري إلى الرسم: ما الذي يساعد جزيئات البخار على تكوين القطرات؟"
    )
    repaired_science, changed_science = ensure_new_canvas_is_not_claimed_visible(
        science, new_composition_requested=True,
    )
    assert changed_science
    assert "في صورة غاز" in repaired_science
    assert "ما الذي يساعد جزيئات البخار" in repaired_science
    assert "انظري إلى الرسم" not in repaired_science

    fractions = (
        "عندما يكون الشكل كله متساويًا، تكون القطعة أكبر إذا قسمناه إلى أجزاء أقل. "
        "انظري إلى الجزأين المظللين في الرسم، ثم اختاري: أي كسر أكبر، 1/3 أم 1/5؟"
    )
    repaired_fractions, changed_fractions = ensure_new_canvas_is_not_claimed_visible(
        fractions, new_composition_requested=True,
    )
    assert changed_fractions
    assert "عندما يكون الشكل كله متساويًا" in repaired_fractions
    assert "أي كسر أكبر، 1/3 أم 1/5؟" in repaired_fractions
    assert "انظري إلى الجزأين" not in repaired_fractions
