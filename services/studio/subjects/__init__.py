"""Production bounded subject profiles and capability registry exports."""

from __future__ import annotations

from functools import lru_cache
from types import MappingProxyType

from services.studio.subjects.contracts import SubjectCapabilityProfile
from services.studio.subjects.arabic_sentence_ordering import ARABIC_PROFILE_VERSION, make_arabic_sentence_ordering_profile
from services.studio.subjects.math_make_ten import MATH_PROFILE_VERSION, make_ten_profile
from services.studio.subjects.process_sequence import SCIENCE_PROFILE_VERSION, make_process_sequence_profile
from services.studio.subjects.sentence_ordering import ENGLISH_PROFILE_VERSION, make_sentence_ordering_profile
from services.studio.subjects.registry import SubjectCapabilityRegistry


PRODUCTION_CURRENT_PROFILE_VERSIONS = MappingProxyType({
    "MATH": MATH_PROFILE_VERSION,
    "SCIENCE": SCIENCE_PROFILE_VERSION,
    "ENGLISH": ENGLISH_PROFILE_VERSION,
    "ARABIC": ARABIC_PROFILE_VERSION,
})


@lru_cache(maxsize=1)
def production_subject_registry() -> SubjectCapabilityRegistry:
    """Return exact production subject profiles, retaining historical profiles for replay."""

    baseline_profiles = tuple(
        SubjectCapabilityProfile(
            subject_key=subject_key,
            profile_version="subject-profile-v1",
            supported_grade_scope=(),
            concept_namespace=f"lina.{subject_key.lower()}",
            tutor_guidance_fragment="subject-guidance-v1",
            grounding_policy_key="question-driven-grounding-v1",
            locale_policy_key="subject-independent-locale-v1",
            deterministic_fallback="safe-text-fallback-v1",
            canvas_specialist_profile_key=None,
        )
        for subject_key in ("MATH", "SCIENCE", "ENGLISH", "ARABIC")
    )
    return SubjectCapabilityRegistry(
        (*baseline_profiles, make_ten_profile(), make_process_sequence_profile(), make_sentence_ordering_profile(), make_arabic_sentence_ordering_profile())
    )


__all__ = ["PRODUCTION_CURRENT_PROFILE_VERSIONS", "SubjectCapabilityProfile", "SubjectCapabilityRegistry", "production_subject_registry"]
