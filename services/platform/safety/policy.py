"""Deterministic MVP policy routing before student-facing Tutor behavior."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import SafetyAudit, StudentTopicBoundary
from services.tutor.parent_boundaries import ParentBoundaryCategory, ParentBoundaryDecision

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


# Kept as a compatibility name for the server-owned Parent configuration API.
# The persisted restricted category is now semantically precise: SEXUAL_CONTENT.
TopicCategory = ParentBoundaryCategory


_DEFAULT_BOUNDARIES = {
    TopicCategory.RELIGION: BoundaryState.REDIRECT_TO_PARENT,
    TopicCategory.SEXUAL_CONTENT: BoundaryState.REDIRECT_TO_PARENT,
    TopicCategory.RELATIONSHIPS: BoundaryState.AGE_APPROPRIATE_ONLY,
    TopicCategory.POLITICS: BoundaryState.AGE_APPROPRIATE_ONLY,
    TopicCategory.DEATH_GRIEF: BoundaryState.AGE_APPROPRIATE_ONLY,
    TopicCategory.FAMILY_FINANCES: BoundaryState.AGE_APPROPRIATE_ONLY,
}
_PROTECTED_BASELINE_PHRASES = (
    "kill myself",
    "hurt myself",
    "make a weapon",
    "لا أريد أن أعيش بعد الآن",
    "لا أريد العيش",
    "أريد أن أؤذي نفسي",
    "سأقتل نفسي",
)
_SAFE_EDUCATIONAL_SELF_HARM_CONTEXT = (
    "health lesson",
    "safe definition",
    "definition safe for a child",
)


@dataclass(frozen=True)
class SafetyDecision:
    action: SafetyAction
    category: TopicCategory | None
    policy_source: str
    policy_version: int
    reason_code: str
    age_handling: str
    directive: str | None


@dataclass(frozen=True)
class ParentBoundaryResolution:
    """Server-owned effective result of Luna's semantic category decision."""

    action: SafetyAction
    category: TopicCategory | None
    policy_source: str
    policy_version: int
    reason_code: str
    boundary_state: BoundaryState | None

    def effective_settings_entry(self) -> tuple[str, str]:
        """Expose only category/action, never Parent-owned implementation details."""

        return (
            self.category.value if self.category is not None else "OPEN_BY_DEFAULT",
            self.action.value,
        )


class SafetyPolicyService:
    """Evaluate hard baseline, then resolve semantic Parent Boundaries server-side."""

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
        if _matches_protected_baseline(normalized):
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

    def effective_parent_boundaries(self, *, student_id: UUID) -> dict[str, str]:
        """Return compact effective settings for the one Luna Tutor call."""

        boundaries = self._boundaries_for_student(student_id=student_id)
        return {
            category.value: BoundaryState(boundaries[category].state).value
            if category in boundaries
            else _DEFAULT_BOUNDARIES[category].value
            for category in TopicCategory
        }

    def resolve_parent_boundary(
        self,
        *,
        student_id: UUID,
        decision: ParentBoundaryDecision | None,
    ) -> ParentBoundaryResolution:
        """Default open on absent/ambiguous semantics; settings beat model action."""

        if decision is None or not decision.applies or decision.category is None:
            return ParentBoundaryResolution(
                action=SafetyAction.ALLOW,
                category=None,
                policy_source="DEFAULT_OPEN",
                policy_version=POLICY_ENGINE_VERSION,
                reason_code="SEMANTIC_NOT_APPLICABLE",
                boundary_state=None,
            )
        boundaries = self._boundaries_for_student(student_id=student_id)
        boundary = boundaries.get(decision.category)
        state = BoundaryState(boundary.state) if boundary is not None else _DEFAULT_BOUNDARIES[decision.category]
        return ParentBoundaryResolution(
            action=SafetyAction(state.value),
            category=decision.category,
            policy_source="PARENT_BOUNDARY" if boundary is not None else "DEFAULT_BOUNDARY",
            policy_version=boundary.policy_version if boundary is not None else POLICY_ENGINE_VERSION,
            reason_code=f"SEMANTIC_TOPIC_{state.value}",
            boundary_state=state,
        )

    def _boundaries_for_student(self, *, student_id: UUID) -> dict[TopicCategory, StudentTopicBoundary]:
        rows = self._session.execute(
            select(StudentTopicBoundary).where(StudentTopicBoundary.student_id == student_id)
        ).scalars()
        resolved: dict[TopicCategory, StudentTopicBoundary] = {}
        for row in rows:
            try:
                category = TopicCategory(row.category)
            except ValueError:
                # Historical values remain stored/auditable but never become a
                # hidden meaning change in the new semantic resolver.
                continue
            resolved[category] = row
        return resolved

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


def _matches_protected_baseline(normalized_text: str) -> bool:
    """Block direct harmful intent while allowing an explicitly safe definition request."""

    if any(phrase in normalized_text for phrase in _PROTECTED_BASELINE_PHRASES):
        return True
    if "suicide" not in normalized_text:
        return False
    return not any(context in normalized_text for context in _SAFE_EDUCATIONAL_SELF_HARM_CONTEXT)
