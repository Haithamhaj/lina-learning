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


def is_supported_broad_subject(value: object) -> bool:
    """Return whether a value is an active Broad Subject registry key."""

    return isinstance(value, str) and value in BROAD_SUBJECT_KEY_SET
