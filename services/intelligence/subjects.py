"""Controlled, versioned Broad Subject registry for learning intelligence."""

from __future__ import annotations

from typing import Final


BROAD_SUBJECT_REGISTRY_VERSION: Final = "broad-subject-registry-v1"
BROAD_SUBJECT_KEYS: Final = (
    "MATH",
    "SCIENCE",
    "LANGUAGE_ARTS",
    "SOCIAL_STUDIES",
    "COMPUTING",
    "RELIGIOUS_STUDIES",
    "ARTS",
    "PHYSICAL_EDUCATION",
    "GENERAL_KNOWLEDGE",
    "OTHER",
)
BROAD_SUBJECT_KEY_SET: Final = frozenset(BROAD_SUBJECT_KEYS)

# Studio academic keys and Learning Intelligence Broad Subjects are distinct
# namespaces even when a key happens to share the same spelling.  This small
# bridge is deliberately fail-closed: a new Studio capability cannot silently
# scope Retrieval, a Learner Intelligence Card, or durable Intelligence.
_STUDIO_TO_BROAD_SUBJECT: Final = {
    "MATH": "MATH",
    "SCIENCE": "SCIENCE",
    "ENGLISH": "LANGUAGE_ARTS",
    "ARABIC": "LANGUAGE_ARTS",
}


def is_supported_broad_subject(value: object) -> bool:
    """Return whether a value is an active Broad Subject registry key."""

    return isinstance(value, str) and value in BROAD_SUBJECT_KEY_SET


def studio_subject_to_broad_subject(subject_key: object) -> str | None:
    """Map one exact Studio academic key to a controlled Broad Subject."""

    mapped = _STUDIO_TO_BROAD_SUBJECT.get(subject_key) if isinstance(subject_key, str) else None
    return mapped if is_supported_broad_subject(mapped) else None
