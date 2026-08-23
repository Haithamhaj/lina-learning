"""Project-owned TeachingMethod registry and current-turn eligibility."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


TEACHING_METHOD_REGISTRY_VERSION = "teaching-method-registry-v1"


class TeachingMethod(str, Enum):
    CONCRETE_EXAMPLE = "CONCRETE_EXAMPLE"
    VISUAL_REPRESENTATION = "VISUAL_REPRESENTATION"
    WORKED_EXAMPLE = "WORKED_EXAMPLE"
    SOCRATIC_FOCUS = "SOCRATIC_FOCUS"
    DECOMPOSITION = "DECOMPOSITION"
    ANALOGY = "ANALOGY"
    SYMBOLIC_EXPLANATION = "SYMBOLIC_EXPLANATION"


@dataclass(frozen=True)
class TeachingMethodDefinition:
    method_id: TeachingMethod
    description: str


@dataclass(frozen=True)
class PriorTeachingMethodContext:
    tutor_message_id: UUID
    teaching_method_id: TeachingMethod
    registry_version: str


_REGISTRY = {
    TeachingMethod.CONCRETE_EXAMPLE: TeachingMethodDefinition(
        TeachingMethod.CONCRETE_EXAMPLE, "Use a familiar concrete example before abstraction."
    ),
    TeachingMethod.VISUAL_REPRESENTATION: TeachingMethodDefinition(
        TeachingMethod.VISUAL_REPRESENTATION, "Use a simple visual or mental representation."
    ),
    TeachingMethod.WORKED_EXAMPLE: TeachingMethodDefinition(
        TeachingMethod.WORKED_EXAMPLE, "Work through one short example clearly."
    ),
    TeachingMethod.SOCRATIC_FOCUS: TeachingMethodDefinition(
        TeachingMethod.SOCRATIC_FOCUS, "Use one focused question to guide the next step."
    ),
    TeachingMethod.DECOMPOSITION: TeachingMethodDefinition(
        TeachingMethod.DECOMPOSITION, "Break the idea into small manageable steps."
    ),
    TeachingMethod.ANALOGY: TeachingMethodDefinition(
        TeachingMethod.ANALOGY, "Use a simple analogy that preserves the concept."
    ),
    TeachingMethod.SYMBOLIC_EXPLANATION: TeachingMethodDefinition(
        TeachingMethod.SYMBOLIC_EXPLANATION, "Explain the relevant mathematical rule or notation simply."
    ),
}

ACTIVE_TEACHING_METHODS = tuple(_REGISTRY)

_STRATEGY_METHODS = {
    "EXPLAIN_THEN_CHECK": (
        TeachingMethod.CONCRETE_EXAMPLE,
        TeachingMethod.VISUAL_REPRESENTATION,
        TeachingMethod.WORKED_EXAMPLE,
        TeachingMethod.DECOMPOSITION,
    ),
    "HINT_FIRST": (
        TeachingMethod.SOCRATIC_FOCUS,
        TeachingMethod.DECOMPOSITION,
        TeachingMethod.CONCRETE_EXAMPLE,
        TeachingMethod.VISUAL_REPRESENTATION,
    ),
    "EXPLAIN_WITH_EXAMPLE": (
        TeachingMethod.CONCRETE_EXAMPLE,
        TeachingMethod.WORKED_EXAMPLE,
        TeachingMethod.ANALOGY,
        TeachingMethod.VISUAL_REPRESENTATION,
    ),
    "INDEPENDENT_CHECK": (
        TeachingMethod.SOCRATIC_FOCUS,
        TeachingMethod.DECOMPOSITION,
        TeachingMethod.SYMBOLIC_EXPLANATION,
    ),
}


def teaching_method_definitions(methods: tuple[TeachingMethod, ...]) -> tuple[TeachingMethodDefinition, ...]:
    """Return only compact definitions for methods eligible in one Tutor turn."""

    return tuple(_REGISTRY[method] for method in methods)


def is_supported_teaching_method(value: object, *, registry_version: object) -> TeachingMethod | None:
    """Accept only active methods from the compiled Registry version."""

    if registry_version != TEACHING_METHOD_REGISTRY_VERSION:
        return None
    try:
        method = TeachingMethod(str(value))
    except ValueError:
        return None
    return method if method in _REGISTRY else None


def prior_teaching_method_context_from_payload(
    *,
    tutor_message_id: UUID,
    payload: object,
) -> PriorTeachingMethodContext | None:
    """Read only a valid, project-owned method identity from Tutor metadata."""

    if not isinstance(payload, dict):
        return None
    registry_version = payload.get("teaching_method_registry_version")
    method = is_supported_teaching_method(
        payload.get("teaching_method_id"),
        registry_version=registry_version,
    )
    if method is None or not isinstance(registry_version, str):
        return None
    return PriorTeachingMethodContext(tutor_message_id, method, registry_version)


def select_eligible_teaching_methods(
    message: str,
    *,
    strategy: str,
    prior_method: PriorTeachingMethodContext | None = None,
) -> tuple[TeachingMethod, ...]:
    """Return current-turn methods without consulting historical intelligence."""

    normalized = message.casefold()
    if _is_non_instructional(normalized):
        return ()
    eligible = list(_STRATEGY_METHODS.get(strategy, _STRATEGY_METHODS["EXPLAIN_WITH_EXAMPLE"]))
    requested = _explicit_request(normalized)
    if requested is not None:
        eligible = [requested, *[method for method in eligible if method != requested]]
    if _continued_confusion(normalized) and prior_method is not None and requested != prior_method.teaching_method_id:
        eligible = [method for method in eligible if method != prior_method.teaching_method_id]
    return tuple(eligible[:4])


def _explicit_request(message: str) -> TeachingMethod | None:
    if any(cue in message for cue in ("برسم", "بالرسم", "رسم", "visual", "draw it")):
        return TeachingMethod.VISUAL_REPRESENTATION
    if any(cue in message for cue in ("مثال", "example")):
        return TeachingMethod.CONCRETE_EXAMPLE
    if any(cue in message for cue in ("خطوة خطوة", "step by step")):
        return TeachingMethod.DECOMPOSITION
    if any(cue in message for cue in ("بالقانون", "القانون", "formula", "rule")):
        return TeachingMethod.SYMBOLIC_EXPLANATION
    return None


def _continued_confusion(message: str) -> bool:
    return any(cue in message for cue in (
        "لسه مش فاهمة", "لسه مش واضحة", "مش فاهمة", "مش واضحة", "لا أفهم", "ما فهمت",
        "still confused", "still not clear", "i don't understand", "don't understand", "stuck",
    ))


def _is_non_instructional(message: str) -> bool:
    return message.strip(" .!؟?👍✨✍️") in {
        "hello", "hi", "thanks", "thank you", "شكراً", "شكرا", "فهمت", "فهمت الآن", "تمام فهمت", "i got it", "i understand", "got it",
    }
