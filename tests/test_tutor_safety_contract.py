"""Contract tests for explicit policy-decision consumption before Tutor work."""

from __future__ import annotations

from services.platform.safety import SafetyAction, SafetyDecision, TopicCategory
from services.tutor.safety import consume_safety_decision


def _decision(
    action: SafetyAction,
    *,
    directive: str | None = None,
) -> SafetyDecision:
    return SafetyDecision(
        action=action,
        category=TopicCategory.RELATIONSHIPS if action is SafetyAction.AGE_APPROPRIATE_ONLY else None,
        policy_source="PARENT_BOUNDARY" if action is not SafetyAction.BLOCK else "BASELINE",
        policy_version=7,
        reason_code=f"TEST_{action.value}",
        age_handling="age_appropriate" if action is SafetyAction.AGE_APPROPRIATE_ONLY else "normal",
        directive=directive,
    )


def test_allow_continues_without_a_tutor_or_redirect_directive() -> None:
    runtime = consume_safety_decision(_decision(SafetyAction.ALLOW))

    assert runtime.action is SafetyAction.ALLOW
    assert runtime.continue_to_tutor is True
    assert runtime.tutor_directive is None
    assert runtime.redirect_directive is None


def test_age_appropriate_action_continues_with_its_policy_directive() -> None:
    runtime = consume_safety_decision(
        _decision(
            SafetyAction.AGE_APPROPRIATE_ONLY,
            directive="Use simple framing and do not provide adult-level detail.",
        )
    )

    assert runtime.action is SafetyAction.AGE_APPROPRIATE_ONLY
    assert runtime.continue_to_tutor is True
    assert runtime.tutor_directive == "Use simple framing and do not provide adult-level detail."
    assert runtime.redirect_directive is None


def test_parent_redirect_stops_tutor_and_preserves_the_calm_policy_directive() -> None:
    runtime = consume_safety_decision(
        _decision(
            SafetyAction.REDIRECT_TO_PARENT,
            directive="Invite Lina to discuss this with a parent, then offer another safe topic.",
        )
    )

    assert runtime.action is SafetyAction.REDIRECT_TO_PARENT
    assert runtime.continue_to_tutor is False
    assert runtime.tutor_directive is None
    assert runtime.redirect_directive == "Invite Lina to discuss this with a parent, then offer another safe topic."


def test_protected_baseline_stops_tutor_with_its_own_directive_and_audit_identity() -> None:
    runtime = consume_safety_decision(
        _decision(
            SafetyAction.BLOCK,
            directive="Give a short safe redirect and encourage a trusted grown-up when appropriate.",
        )
    )

    assert runtime.action is SafetyAction.BLOCK
    assert runtime.continue_to_tutor is False
    assert runtime.redirect_directive == "Give a short safe redirect and encourage a trusted grown-up when appropriate."
    assert runtime.audit_metadata() == {
        "action": "BLOCK",
        "policy_source": "BASELINE",
        "policy_version": 7,
        "reason_code": "TEST_BLOCK",
    }
