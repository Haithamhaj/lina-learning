"""Project-owned frozen TeachingMethod registry."""

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
        TeachingMethod.CONCRETE_EXAMPLE, "Use a familiar concrete example to make an abstract idea meaningful, connecting it to the concept rather than treating the story as decoration."
    ),
    TeachingMethod.VISUAL_REPRESENTATION: TeachingMethodDefinition(
        TeachingMethod.VISUAL_REPRESENTATION, "Use a simple visual or mental representation to expose structure. A mental description is not a displayed picture or Canvas."
    ),
    TeachingMethod.WORKED_EXAMPLE: TeachingMethodDefinition(
        TeachingMethod.WORKED_EXAMPLE, "Work through one short example, showing the key reasoning and why each useful step follows; avoid merely listing operations."
    ),
    TeachingMethod.SOCRATIC_FOCUS: TeachingMethodDefinition(
        TeachingMethod.SOCRATIC_FOCUS, "Use one focused question to help the Student notice, predict or reason about the next step when they have enough foundation to engage."
    ),
    TeachingMethod.DECOMPOSITION: TeachingMethodDefinition(
        TeachingMethod.DECOMPOSITION, "Break an idea into manageable parts or steps and make their relationship to the whole explicit."
    ),
    TeachingMethod.ANALOGY: TeachingMethodDefinition(
        TeachingMethod.ANALOGY, "Use a simple analogy that preserves the relevant concept and does not import misleading relationships."
    ),
    TeachingMethod.SYMBOLIC_EXPLANATION: TeachingMethodDefinition(
        TeachingMethod.SYMBOLIC_EXPLANATION, "Explain the relevant mathematical rule or notation simply and connect the symbols to their meaning."
    ),
}

ACTIVE_TEACHING_METHODS = tuple(_REGISTRY)

def teaching_method_definitions() -> tuple[TeachingMethodDefinition, ...]:
    """Return compact definitions for every active method Luna may select."""

    return tuple(_REGISTRY[method] for method in ACTIVE_TEACHING_METHODS)


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
