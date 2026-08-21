"""Deterministic MVP policy routing before student-facing Tutor behavior."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import SafetyAudit, StudentTopicBoundary

POLICY_ENGINE_VERSION = 1

AGE_APPROPRIATE_DIRECTIVE = (
    "Continue the conversation with simple, age-appropriate framing and without adult-level detail."
)
PARENT_REDIRECT_DIRECTIVE = (
    "This is a topic that is best to discuss with a parent. We can continue with another safe learning topic."
)
PROTECTED_BASELINE_DIRECTIVE = (
    "I can’t help with that. Please talk to a trusted grown-up who can support you."
)


class BoundaryState(str, Enum):
    ALLOW = "ALLOW"
    AGE_APPROPRIATE_ONLY = "AGE_APPROPRIATE_ONLY"
    REDIRECT_TO_PARENT = "REDIRECT_TO_PARENT"


class SafetyAction(str, Enum):
    ALLOW = "ALLOW"
    AGE_APPROPRIATE_ONLY = "AGE_APPROPRIATE_ONLY"
    REDIRECT_TO_PARENT = "REDIRECT_TO_PARENT"
    BLOCK = "BLOCK"


class TopicCategory(str, Enum):
    RELIGION = "RELIGION"
    HUMAN_REPRODUCTION = "HUMAN_REPRODUCTION"
    RELATIONSHIPS = "RELATIONSHIPS"
    POLITICS = "POLITICS"
    DEATH_GRIEF = "DEATH_GRIEF"
    FAMILY_FINANCES = "FAMILY_FINANCES"


_DEFAULT_BOUNDARIES = {
    TopicCategory.RELIGION: BoundaryState.REDIRECT_TO_PARENT,
    TopicCategory.HUMAN_REPRODUCTION: BoundaryState.REDIRECT_TO_PARENT,
    TopicCategory.RELATIONSHIPS: BoundaryState.AGE_APPROPRIATE_ONLY,
    TopicCategory.POLITICS: BoundaryState.AGE_APPROPRIATE_ONLY,
    TopicCategory.DEATH_GRIEF: BoundaryState.AGE_APPROPRIATE_ONLY,
    TopicCategory.FAMILY_FINANCES: BoundaryState.AGE_APPROPRIATE_ONLY,
}
_BASELINE_TERMS = ("suicide", "kill myself", "hurt myself", "make a weapon")
_CATEGORY_TERMS = {
    TopicCategory.RELIGION: ("prayer", "religion", "god", "mosque"),
    TopicCategory.HUMAN_REPRODUCTION: ("sex education", "reproduction"),
    TopicCategory.RELATIONSHIPS: ("dating", "boyfriend", "girlfriend"),
    TopicCategory.POLITICS: ("politics", "election", "president"),
    TopicCategory.DEATH_GRIEF: ("death", "died", "grief"),
    TopicCategory.FAMILY_FINANCES: ("family money", "our debt", "salary"),
}


@dataclass(frozen=True)
class SafetyDecision:
    action: SafetyAction
    category: TopicCategory | None
    policy_source: str
    policy_version: int
    reason_code: str
    age_handling: str
    directive: str | None


class SafetyPolicyService:
    """Evaluate protected baseline first, then persistent family boundaries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def set_boundary(
        self,
        *,
        student_id: UUID,
        category: TopicCategory | str,
        state: BoundaryState,
    ) -> StudentTopicBoundary:
        try:
            topic = TopicCategory(category)
        except ValueError as error:
            raise ValueError("Only configurable topic categories may be changed.") from error

        boundary = self._session.execute(
            select(StudentTopicBoundary).where(
                StudentTopicBoundary.student_id == student_id,
                StudentTopicBoundary.category == topic.value,
            )
        ).scalar_one_or_none()
        if boundary is None:
            boundary = StudentTopicBoundary(
                student_id=student_id,
                category=topic.value,
                state=state.value,
                policy_version=1,
            )
            self._session.add(boundary)
        else:
            boundary.state = state.value
            boundary.policy_version += 1
        self._session.flush()
        return boundary

    def evaluate(
        self,
        *,
        student_id: UUID,
        text: str,
        interaction_ref: str | None = None,
    ) -> SafetyDecision:
        normalized = text.lower()
        if any(term in normalized for term in _BASELINE_TERMS):
            return self._audit(
                student_id,
                interaction_ref,
                SafetyDecision(
                    action=SafetyAction.BLOCK,
                    category=None,
                    policy_source="BASELINE",
                    policy_version=POLICY_ENGINE_VERSION,
                    reason_code="PROTECTED_BASELINE",
                    age_handling="safe_redirect",
                    directive=PROTECTED_BASELINE_DIRECTIVE,
                ),
            )

        category = next(
            (topic for topic, terms in _CATEGORY_TERMS.items() if any(term in normalized for term in terms)),
            None,
        )
        if category is None:
            return self._audit(
                student_id,
                interaction_ref,
                SafetyDecision(
                    action=SafetyAction.ALLOW,
                    category=None,
                    policy_source="BASELINE",
                    policy_version=POLICY_ENGINE_VERSION,
                    reason_code="NORMAL_LEARNING",
                    age_handling="normal",
                    directive=None,
                ),
            )

        boundary = self._session.execute(
            select(StudentTopicBoundary).where(
                StudentTopicBoundary.student_id == student_id,
                StudentTopicBoundary.category == category.value,
            )
        ).scalar_one_or_none()
        state = BoundaryState(boundary.state) if boundary else _DEFAULT_BOUNDARIES[category]
        return self._audit(
            student_id,
            interaction_ref,
            SafetyDecision(
                action=SafetyAction(state.value),
                category=category,
                policy_source="PARENT_BOUNDARY" if boundary else "DEFAULT_BOUNDARY",
                policy_version=boundary.policy_version if boundary else POLICY_ENGINE_VERSION,
                reason_code=f"TOPIC_{state.value}",
                age_handling="age_appropriate" if state == BoundaryState.AGE_APPROPRIATE_ONLY else "normal",
                directive=(
                    AGE_APPROPRIATE_DIRECTIVE
                    if state == BoundaryState.AGE_APPROPRIATE_ONLY
                    else PARENT_REDIRECT_DIRECTIVE
                    if state == BoundaryState.REDIRECT_TO_PARENT
                    else None
                ),
            ),
        )

    def _audit(
        self,
        student_id: UUID,
        interaction_ref: str | None,
        decision: SafetyDecision,
    ) -> SafetyDecision:
        self._session.add(
            SafetyAudit(
                student_id=student_id,
                interaction_ref=interaction_ref,
                category=decision.category.value if decision.category else None,
                policy_source=decision.policy_source,
                action=decision.action.value,
                reason_code=decision.reason_code,
                policy_version=decision.policy_version,
            )
        )
        self._session.flush()
        return decision
