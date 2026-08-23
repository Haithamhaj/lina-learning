"""Deterministic TeachingMethod registry and eligibility contracts."""

from uuid import uuid4

import pytest

from services.tutor.teaching_methods import (
    ACTIVE_TEACHING_METHODS,
    TEACHING_METHOD_REGISTRY_VERSION,
    PriorTeachingMethodContext,
    TeachingMethod,
    select_eligible_teaching_methods,
)


def test_active_registry_exposes_only_the_approved_versioned_methods() -> None:
    """Catches a frozen Artifact/Vision method accidentally becoming eligible."""

    assert TEACHING_METHOD_REGISTRY_VERSION == "teaching-method-registry-v1"
    assert set(ACTIVE_TEACHING_METHODS) == {
        TeachingMethod.CONCRETE_EXAMPLE,
        TeachingMethod.VISUAL_REPRESENTATION,
        TeachingMethod.WORKED_EXAMPLE,
        TeachingMethod.SOCRATIC_FOCUS,
        TeachingMethod.DECOMPOSITION,
        TeachingMethod.ANALOGY,
        TeachingMethod.SYMBOLIC_EXPLANATION,
    }


@pytest.mark.parametrize(
    ("message", "strategy", "expected"),
    [
        ("ورجيني برسم", "EXPLAIN_WITH_EXAMPLE", TeachingMethod.VISUAL_REPRESENTATION),
        ("اعطيني مثال", "EXPLAIN_WITH_EXAMPLE", TeachingMethod.CONCRETE_EXAMPLE),
        ("ممكن خطوة خطوة", "EXPLAIN_THEN_CHECK", TeachingMethod.DECOMPOSITION),
        ("اشرحلي بالقانون", "EXPLAIN_WITH_EXAMPLE", TeachingMethod.SYMBOLIC_EXPLANATION),
    ],
)
def test_explicit_current_method_requests_are_eligible(
    message: str,
    strategy: str,
    expected: TeachingMethod,
) -> None:
    """Catches a current explicit representation request being ignored."""

    eligible = select_eligible_teaching_methods(message, strategy=strategy)

    assert expected in eligible
    assert 2 <= len(eligible) <= 4


def test_current_confusion_excludes_the_previous_persisted_method() -> None:
    """Catches a confused Student receiving the same failed representation again."""

    prior = PriorTeachingMethodContext(
        tutor_message_id=uuid4(),
        teaching_method_id=TeachingMethod.SYMBOLIC_EXPLANATION,
        registry_version=TEACHING_METHOD_REGISTRY_VERSION,
    )

    eligible = select_eligible_teaching_methods(
        "لسه مش فاهمة",
        strategy="EXPLAIN_THEN_CHECK",
        prior_method=prior,
    )

    assert TeachingMethod.SYMBOLIC_EXPLANATION not in eligible
    assert 2 <= len(eligible) <= 4


def test_explicit_same_representation_request_overrides_confusion_switching() -> None:
    """Catches a direct request for the same visual method being suppressed."""

    prior = PriorTeachingMethodContext(
        tutor_message_id=uuid4(),
        teaching_method_id=TeachingMethod.VISUAL_REPRESENTATION,
        registry_version=TEACHING_METHOD_REGISTRY_VERSION,
    )

    eligible = select_eligible_teaching_methods(
        "لسه مش فاهمة، ورجيني بالرسم مرة ثانية",
        strategy="EXPLAIN_THEN_CHECK",
        prior_method=prior,
    )

    assert TeachingMethod.VISUAL_REPRESENTATION in eligible


def test_non_instructional_message_has_no_eligible_teaching_method() -> None:
    """Catches method attribution on a greeting that receives no teaching."""

    assert select_eligible_teaching_methods("شكراً", strategy="EXPLAIN_WITH_EXAMPLE") == ()
