"""Compact, server-owned Workspace capability context for the primary Tutor request."""

from __future__ import annotations

from dataclasses import dataclass

from services.studio.subjects import PRODUCTION_CURRENT_PROFILE_VERSIONS, production_subject_registry
from services.studio.subjects.registry import SubjectCapabilityError
from services.studio.subjects.decimal_number_line import authored_problem_sources
from services.studio.subjects.decimal_place_value import authored_problem_sources as place_value_sources
from services.studio.tutor_context import StudioTutorWorkspaceContext


WORKSPACE_CAPABILITY_CONTEXT_VERSION = "workspace-capability-context-v1"


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
        return WorkspaceCapabilityContext(None, None, None, "NO_STUDIO_RUNTIME", (), authorized_source_references, False, False)
    scene = studio_context.current_scene_capability
    subject_key = scene.subject_key if scene is not None else (current_subject_key or studio_context.active_subject_key)
    profile_version = scene.subject_profile_version if scene is not None else PRODUCTION_CURRENT_PROFILE_VERSIONS.get(subject_key or "")
    active_scene_status = "NO_ACTIVE_SCENE" if scene is None else scene.capability_status
    if subject_key is None or profile_version is None:
        return WorkspaceCapabilityContext(subject_key, profile_version, None, active_scene_status, (), authorized_source_references, False, False)
    try:
        profile = production_subject_registry().resolve_profile(subject_key, profile_version)
    except SubjectCapabilityError:
        return WorkspaceCapabilityContext(subject_key, profile_version, None, "UNSUPPORTED_HISTORICAL_CAPABILITY", (), authorized_source_references, False, False)
    problems = authored_problem_sources(subject_key) + place_value_sources(subject_key)
    return WorkspaceCapabilityContext(
        subject_key, profile_version, profile.tutor_guidance_fragment, active_scene_status,
        () if scene is None else scene.allowed_action_keys,
        tuple(dict.fromkeys((*authorized_source_references, *(p['source_ref'] for p in problems)))),
        bool(profile.activities),
        profile.canvas_specialist_profile_key is not None,
        problems,
    )
