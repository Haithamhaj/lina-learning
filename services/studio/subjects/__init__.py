"""Production bounded subject profiles and capability registry exports."""

from __future__ import annotations

from functools import lru_cache

from services.studio.subjects.contracts import SubjectCapabilityProfile
from services.studio.subjects.registry import SubjectCapabilityRegistry


@lru_cache(maxsize=1)
def production_subject_registry() -> SubjectCapabilityRegistry:
    """Return only production subject identities; teaching activities register in later tasks."""

    profiles = tuple(
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
    return SubjectCapabilityRegistry(profiles)


__all__ = ["SubjectCapabilityProfile", "SubjectCapabilityRegistry", "production_subject_registry"]
