"""Translate policy decisions into explicit pre-Tutor runtime behavior."""

from __future__ import annotations

from dataclasses import dataclass

from services.platform.safety import SafetyAction, SafetyDecision


@dataclass(frozen=True)
class TutorSafetyRuntime:
    """The complete policy result the Tutor runtime must consume."""

    action: SafetyAction
    policy_source: str
    policy_version: int
    reason_code: str
    continue_to_tutor: bool
    tutor_directive: str | None = None
    redirect_directive: str | None = None

    def audit_metadata(self) -> dict[str, str | int]:
        """Keep downstream handling linked to the persisted policy decision."""

        return {
            "action": self.action.value,
            "policy_source": self.policy_source,
            "policy_version": self.policy_version,
            "reason_code": self.reason_code,
        }


def consume_safety_decision(decision: SafetyDecision) -> TutorSafetyRuntime:
    """Map every approved policy action explicitly; never collapse non-ALLOW actions."""

    metadata = {
        "action": decision.action,
        "policy_source": decision.policy_source,
        "policy_version": decision.policy_version,
        "reason_code": decision.reason_code,
    }
    if decision.action is SafetyAction.ALLOW:
        return TutorSafetyRuntime(continue_to_tutor=True, **metadata)
    if decision.action is SafetyAction.AGE_APPROPRIATE_ONLY:
        return TutorSafetyRuntime(
            continue_to_tutor=True,
            tutor_directive=decision.directive,
            **metadata,
        )
    if decision.action is SafetyAction.REDIRECT_TO_PARENT:
        return TutorSafetyRuntime(
            continue_to_tutor=False,
            redirect_directive=decision.directive,
            **metadata,
        )
    if decision.action is SafetyAction.BLOCK:
        return TutorSafetyRuntime(
            continue_to_tutor=False,
            redirect_directive=decision.directive,
            **metadata,
        )
    raise ValueError(f"Unsupported safety action: {decision.action}")
