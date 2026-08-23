"""Canonical semantic decision values returned by the one primary Tutor call."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TeachingMode(str, Enum):
    LEARN = "LEARN"
    HOMEWORK = "HOMEWORK"
    EXPLORE = "EXPLORE"
    REVIEW = "REVIEW"
    QUIZ = "QUIZ"


class TeachingStrategy(str, Enum):
    EXPLAIN_WITH_EXAMPLE = "EXPLAIN_WITH_EXAMPLE"
    HINT_FIRST = "HINT_FIRST"
    EXPLAIN_THEN_CHECK = "EXPLAIN_THEN_CHECK"
    INDEPENDENT_CHECK = "INDEPENDENT_CHECK"


class PriorMethodRelation(str, Enum):
    CONTINUATION = "CONTINUATION"
    DID_NOT_HELP = "DID_NOT_HELP"
    HELPED = "HELPED"
    EXPLICIT_REPEAT_REQUEST = "EXPLICIT_REPEAT_REQUEST"
    NOT_RELEVANT = "NOT_RELEVANT"


@dataclass(frozen=True)
class TeachingDecisionDefinition:
    identifier: str
    description: str


TEACHING_MODE_DEFINITIONS = (
    TeachingDecisionDefinition("LEARN", "Normal concept learning or explanation."),
    TeachingDecisionDefinition("HOMEWORK", "Working with an assigned, class, or homework task."),
    TeachingDecisionDefinition("EXPLORE", "Open curiosity or learning outside the immediate school path."),
    TeachingDecisionDefinition("REVIEW", "Revisiting previously learned material or checking retention."),
    TeachingDecisionDefinition("QUIZ", "Student-requested testing or checking interaction."),
)

TEACHING_STRATEGY_DEFINITIONS = (
    TeachingDecisionDefinition("EXPLAIN_WITH_EXAMPLE", "Provide an initial concise explanation or example, then interact."),
    TeachingDecisionDefinition("HINT_FIRST", "Preserve a meaningful Student attempt before giving stronger teaching."),
    TeachingDecisionDefinition("EXPLAIN_THEN_CHECK", "Teach an unclear idea, then check application or understanding."),
    TeachingDecisionDefinition("INDEPENDENT_CHECK", "Let Lina solve, explain, apply, or demonstrate with minimal support."),
)

PRIOR_METHOD_RELATION_DEFINITIONS = (
    TeachingDecisionDefinition("CONTINUATION", "The prior method remains relevant without a clear helped or failed judgment."),
    TeachingDecisionDefinition("DID_NOT_HELP", "The immediately prior representation did not sufficiently help or clarify."),
    TeachingDecisionDefinition("HELPED", "The prior method helped conversationally; this is not effectiveness Evidence."),
    TeachingDecisionDefinition("EXPLICIT_REPEAT_REQUEST", "Lina explicitly asks to repeat the same prior representation."),
    TeachingDecisionDefinition("NOT_RELEVANT", "A prior method exists but is not relevant to this learning turn or topic."),
)


def parse_enum(value: object, enum_type: type[Enum]) -> Enum | None:
    if value is None:
        return None
    try:
        return enum_type(str(value))
    except ValueError:
        return None
