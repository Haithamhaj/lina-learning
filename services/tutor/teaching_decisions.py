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
    TeachingDecisionDefinition("CONTINUATION", "The immediate prior method remains relevant and the Student has not clearly judged it helped, failed, or requested its repetition."),
    TeachingDecisionDefinition("DID_NOT_HELP", "The Student clearly says the immediate prior representation did not help, clarify, remains confusing, or should change."),
    TeachingDecisionDefinition("HELPED", "The Student clearly says the immediate prior representation helped or clarified; this is not effectiveness Evidence."),
    TeachingDecisionDefinition("EXPLICIT_REPEAT_REQUEST", "Lina explicitly asks to repeat the same prior representation."),
    TeachingDecisionDefinition("NOT_RELEVANT", "A prior method exists but is genuinely unrelated to this learning turn or topic, such as a true topic or goal switch."),
)


PRIOR_METHOD_RELATION_CALIBRATION_GUIDANCE = (
    "PriorMethodRelation calibration: CONTINUATION applies when the immediate prior method remains relevant and the Student has not clearly evaluated it as helping, failing, or needing repetition. "
    "Examples: \"وبعدين؟\" → CONTINUATION; \"طيب الخطوة الجاية؟\" → CONTINUATION; \"what next?\" → CONTINUATION; \"2 من 4\" → CONTINUATION when it directly answers the immediately prior Tutor question. "
    "Do not infer DID_NOT_HELP from a short follow-up, direct answer, continued work, wrong answer, or need for more teaching. "
    "DID_NOT_HELP requires a clear Student signal that the immediate prior representation did not help, did not clarify, remains confusing, or should change. "
    "HELPED requires the Student to clearly say the immediate prior representation helped or clarified. Examples: \"آه هلا فهمت\" → HELPED; \"That makes sense now.\" → HELPED. Do not infer HELPED merely from a correct answer. "
    "EXPLICIT_REPEAT_REQUEST requires an explicit request to repeat or use the same immediate prior representation. "
    "NOT_RELEVANT applies when that method is genuinely unrelated to a new learning topic or goal, not an ordinary continuation. "
    "Use null when no valid immediate prior persisted TeachingMethod exists or no meaningful relation can safely be asserted."
)


def parse_enum(value: object, enum_type: type[Enum]) -> Enum | None:
    if value is None:
        return None
    try:
        return enum_type(str(value))
    except ValueError:
        return None
