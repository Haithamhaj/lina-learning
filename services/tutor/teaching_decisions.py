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
    TeachingDecisionDefinition("LEARN", "Normal concept learning: choose the next useful move, which may be explanation, modeling, practice, comparison, or exploration; it is not explanation-first."),
    TeachingDecisionDefinition("HOMEWORK", "Working on an assigned, class or homework task. Preserve a meaningful attempt while providing teaching when needed; the task is not automatically a quiz."),
    TeachingDecisionDefinition("EXPLORE", "Following curiosity or exploring beyond the immediate school task. Keep the Student's question central without turning every exploration into a lesson or test."),
    TeachingDecisionDefinition("REVIEW", "Revisiting previously encountered learning. Use recall, explanation or application as useful; do not invent a review schedule or assume retention."),
    TeachingDecisionDefinition("QUIZ", "A Student-requested testing or checking interaction; ordinary practice is not automatically a quiz."),
)

TEACHING_STRATEGY_DEFINITIONS = (
    TeachingDecisionDefinition("EXPLAIN_WITH_EXAMPLE", "Make the idea understandable through a concise explanation linked to a relevant example. Select this when that is the useful move, not as a universal entry into learning."),
    TeachingDecisionDefinition("HINT_FIRST", "Support an in-progress Student attempt with a targeted hint when useful progress is possible; give stronger teaching when hints do not restore thinking."),
    TeachingDecisionDefinition("EXPLAIN_THEN_CHECK", "Teach an unclear idea and provide a directly related opportunity to apply or explain it when useful. The check concerns the taught idea, not a generic follow-up question."),
    TeachingDecisionDefinition("INDEPENDENT_CHECK", "Give the Student a meaningful opportunity to solve, explain or apply with minimal task-specific support. It can occur during learning or practice and is not a mastery claim."),
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
    "DID_NOT_HELP requires a clear Student signal that the immediate prior representation did not help, did not clarify, remains confusing, or should change; a missing, delayed, or unavailable visual UI is not a judgment of method effectiveness. "
    "HELPED requires the Student to clearly say the immediate prior representation helped or clarified. Examples: \"آه هلا فهمت\" → HELPED; \"That makes sense now.\" → HELPED. Do not infer HELPED merely from a correct answer. "
    "EXPLICIT_REPEAT_REQUEST requires an explicit request to repeat or use the same immediate prior representation. "
    "NOT_RELEVANT applies when that method is genuinely unrelated to a new learning topic or goal, not an ordinary continuation. "
    "Use null when no valid immediate prior persisted TeachingMethod exists or no meaningful relation can safely be asserted. "
    "A complaint that a visual has not appeared is delivery feedback, not by itself a judgment that an experienced TeachingMethod did not help. A status request or unclear text is not an explicit request to repeat a method. For a purely operational reply without a meaningful teaching move, use null teaching fields and null PriorMethodRelation; conversation continuity is decided separately."
)


def parse_enum(value: object, enum_type: type[Enum]) -> Enum | None:
    if value is None:
        return None
    try:
        return enum_type(str(value))
    except ValueError:
        return None
