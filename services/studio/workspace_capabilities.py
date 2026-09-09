"""Compact, server-owned Workspace capability context for the primary Tutor request."""

from __future__ import annotations

from dataclasses import dataclass

from services.studio.coordinate_plane import COORDINATE_MAX, COORDINATE_MIN
from services.studio.subjects import PRODUCTION_CURRENT_PROFILE_VERSIONS, production_subject_registry
from services.studio.subjects.registry import SubjectCapabilityError
from services.studio.subjects.decimal_number_line import authored_problem_sources
from services.studio.subjects.decimal_place_value import authored_problem_sources as place_value_sources
from services.studio.tutor_context import StudioTutorWorkspaceContext


WORKSPACE_CAPABILITY_CONTEXT_VERSION = "workspace-capability-context-v1"
CUSTOM_COMPOSITION_PATTERNS_BY_PRIMARY_SUBJECT = {
    "MATH": ("SPATIAL_MANIPULATION", "MATH_VISUALIZATION", "MATH_INPUT"),
    "SCIENCE": ("PROCESS",),
    "ENGLISH": (),
    "ARABIC": (),
}
CUSTOM_COMPOSITION_CONSTRAINTS = {
    "PROCESS": {"topologies": ["SEQUENCE", "CYCLE"], "stage_count": [2, 8]},
    "SPATIAL_MANIPULATION": {
        "object_count": 1,
        "target_count": 1,
        "relations": ["INSIDE", "MATCH", "GROUP"],
    },
    "MATH_VISUALIZATION": {
        "construction_family": "CARTESIAN_POINT",
        "coordinate_bounds": [COORDINATE_MIN, COORDINATE_MAX],
        "point_count": 1,
    },
    "MATH_INPUT": {"input_representation": "LATEX", "expression_max_length": 120},
}


@dataclass(frozen=True)
class WorkspaceCapabilityContext:
    subject_key: str | None
    subject_profile_version: str | None
    tutor_guidance_fragment: str | None
    active_scene_status: str
    allowed_action_keys: tuple[str, ...]
    authorized_source_references: tuple[str, ...]
    known_workspace_capabilities_available: bool
    custom_compose_potentially_eligible: bool
    eligible_custom_composition_patterns: tuple[str, ...]
    authored_problem_sources: tuple[dict, ...] = ()

    def as_model_payload(self) -> dict[str, object]:
        return {
            "schema_version": WORKSPACE_CAPABILITY_CONTEXT_VERSION,
            "subject_key": self.subject_key,
            "subject_profile_version": self.subject_profile_version,
            "tutor_guidance_fragment": self.tutor_guidance_fragment,
            "active_scene_status": self.active_scene_status,
            "allowed_action_keys": list(self.allowed_action_keys),
            "authorized_source_references": list(self.authorized_source_references),
            "known_workspace_capabilities_available": self.known_workspace_capabilities_available,
            "custom_compose_potentially_eligible": self.custom_compose_potentially_eligible,
            "eligible_custom_composition_patterns": list(self.eligible_custom_composition_patterns),
            "custom_composition_constraints": {
                pattern: CUSTOM_COMPOSITION_CONSTRAINTS[pattern]
                for pattern in self.eligible_custom_composition_patterns
            },
            "authored_problem_sources": list(self.authored_problem_sources),
        }


def build_workspace_capability_context(
    studio_context: StudioTutorWorkspaceContext | None,
    *,
    authorized_source_references: tuple[str, ...],
    current_subject_key: str | None = None,
) -> WorkspaceCapabilityContext:
    """Represent only currently usable, exact capabilities; absent means unavailable."""

    if studio_context is None:
        return WorkspaceCapabilityContext(None, None, None, "NO_STUDIO_RUNTIME", (), authorized_source_references, False, False, ())
    scene = studio_context.current_scene_capability
    # Studio owns capability identity. Broad Subject is only a fallback when the
    # Workspace has not established one of its four primary subject keys.
    subject_key = scene.subject_key if scene is not None else (studio_context.active_subject_key or current_subject_key)
    profile_version = scene.subject_profile_version if scene is not None else PRODUCTION_CURRENT_PROFILE_VERSIONS.get(subject_key or "")
    active_scene_status = "NO_ACTIVE_SCENE" if scene is None else scene.capability_status
    eligible_custom_patterns = _eligible_custom_composition_patterns(subject_key)
    if subject_key is None or profile_version is None:
        return WorkspaceCapabilityContext(
            subject_key, profile_version, None, active_scene_status, (), authorized_source_references,
            False, bool(eligible_custom_patterns), eligible_custom_patterns,
        )
    try:
        profile = production_subject_registry().resolve_profile(subject_key, profile_version)
    except SubjectCapabilityError:
        return WorkspaceCapabilityContext(subject_key, profile_version, None, "UNSUPPORTED_HISTORICAL_CAPABILITY", (), authorized_source_references, False, False, ())
    problems = authored_problem_sources(subject_key) + place_value_sources(subject_key)
    return WorkspaceCapabilityContext(
        subject_key, profile_version, profile.tutor_guidance_fragment, active_scene_status,
        () if scene is None else scene.allowed_action_keys,
        tuple(dict.fromkeys((*authorized_source_references, *(p['source_ref'] for p in problems)))),
        any(r.implementation_status != "AWARENESS_ONLY" for r in profile.renderers) and bool(profile.activities),
        bool(eligible_custom_patterns),
        eligible_custom_patterns,
        problems,
    )


def _eligible_custom_composition_patterns(
    subject_key: str | None,
) -> tuple[str, ...]:
    """Expose composition only when its current Scene subject would stay truthful."""

    return CUSTOM_COMPOSITION_PATTERNS_BY_PRIMARY_SUBJECT.get(subject_key, ())
