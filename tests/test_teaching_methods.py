"""Deterministic TeachingMethod registry contracts."""

from services.tutor.teaching_methods import (
    ACTIVE_TEACHING_METHODS,
    TEACHING_METHOD_REGISTRY_VERSION,
    TeachingMethod,
    teaching_method_definitions,
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


def test_registry_supplies_all_active_compact_definitions_without_selection_authority() -> None:
    """The frozen registry names valid methods; Luna decides when any applies."""

    definitions = teaching_method_definitions()

    assert [definition.method_id for definition in definitions] == list(ACTIVE_TEACHING_METHODS)
    assert all(definition.description for definition in definitions)
