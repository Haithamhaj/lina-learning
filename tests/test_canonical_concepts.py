"""Contracts for deterministic conversational Concept identity."""

from __future__ import annotations

import pytest

from services.intelligence.concepts import CanonicalConceptRegistry, ConceptRegistryValidationError


def test_registry_maps_arabic_and_english_aliases_to_one_canonical_concept() -> None:
    """Catches alias normalization drifting into separate conversational Concepts."""

    registry = CanonicalConceptRegistry.from_payload(
        version="concept-registry-v1",
        payload={"concepts": [{
            "concept_key": "math.long_division",
            "broad_subject": "MATH",
            "display_name_en": "Long Division",
            "display_name_ar": "القسمة المطولة",
            "aliases": ["long division", "long-division", "القسمة المطولة"],
        }]},
    )

    assert registry.resolve(subject="MATH", concept_ref=" long_division ").concept_key == "math.long_division"
    assert registry.resolve(subject="MATH", concept_ref="القسمة المطولة").concept_key == "math.long_division"
    assert registry.resolve(subject="MATH", concept_ref="unknown topic").status == "UNMAPPED"


def test_registry_rejects_normalized_alias_collision_within_subject() -> None:
    """Catches ambiguous mapping that would silently choose learner context."""

    with pytest.raises(ConceptRegistryValidationError):
        CanonicalConceptRegistry.from_payload(
            version="concept-registry-v1",
            payload={"concepts": [
                {"concept_key": "math.a", "broad_subject": "MATH", "display_name_en": "A", "display_name_ar": "أ", "aliases": ["long-division"]},
                {"concept_key": "math.b", "broad_subject": "MATH", "display_name_en": "B", "display_name_ar": "ب", "aliases": ["long division"]},
            ]},
        )
