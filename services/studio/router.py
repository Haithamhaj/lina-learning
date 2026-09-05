"""Deterministic, non-mutating Runtime-02 Workspace execution decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

from services.studio.subjects.contracts import ActivityContract, RendererContract, SubjectCapabilityProfile
from services.studio.subjects.registry import SubjectCapabilityError, SubjectCapabilityRegistry
from services.studio.workspace_intent import WorkspaceIntent


WORKSPACE_EXECUTION_DECISION_VERSION = "workspace-execution-decision-v1"


class WorkspaceDecisionStatus(str, Enum):
    NO_CHANGE = "NO_CHANGE"
    PRESERVE_ACTIVE_SCENE = "PRESERVE_ACTIVE_SCENE"
    CLOSE_ACTIVE_SCENE = "CLOSE_ACTIVE_SCENE"
    ROUTED = "ROUTED"
    FALLBACK = "FALLBACK"


class WorkspaceExecutionMode(str, Enum):
    SOURCE_VIEW = "SOURCE_VIEW"
    ANNOTATION = "ANNOTATION"
    KNOWN_VISUAL = "KNOWN_VISUAL"
    KNOWN_INTERACTIVE = "KNOWN_INTERACTIVE"
    CUSTOM_COMPOSE = "CUSTOM_COMPOSE"


@dataclass(frozen=True)
class ActiveSceneCapability:
    """Exact persisted Scene contract identity, supplied only by authoritative Studio state."""

    scene_id: str
    subject_key: str
    subject_profile_version: str
    activity_key: str
    activity_version: str
    renderer_key: str
    renderer_version: str
    source_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkspaceAuthorityContext:
    """Server-owned context; no identity in the Tutor request controls these values."""

    active_scene_id: str | None = None
    active_subject_key: str | None = None
    active_scene: ActiveSceneCapability | None = None
    authorized_source_references: tuple[str, ...] = ()
    registry: SubjectCapabilityRegistry | None = None
    current_profile_versions: Mapping[str, str] = field(default_factory=dict)
    current_activity_versions: Mapping[tuple[str, str, str], str] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkspaceExecutionDecision:
    """A bounded plan for future adapters, never a direct Studio-state mutation."""

    version: str
    status: WorkspaceDecisionStatus
    mode: WorkspaceExecutionMode | None
    reason_code: str
    target_scene_id: str | None
    target_source_reference: str | None
    selected_subject_key: str | None = None
    selected_profile_version: str | None = None
    selected_activity_key: str | None = None
    selected_activity_version: str | None = None
    selected_renderer_key: str | None = None
    selected_renderer_version: str | None = None

    @property
    def requires_state_mutation(self) -> bool:
        return False

    def as_audit_payload(self) -> dict[str, object]:
        return {
            "version": self.version,
            "status": self.status.value,
            "mode": None if self.mode is None else self.mode.value,
            "reason_code": self.reason_code,
            "target_scene_id": self.target_scene_id,
            "target_source_reference": self.target_source_reference,
            "selected_subject_key": self.selected_subject_key,
            "selected_profile_version": self.selected_profile_version,
            "selected_activity_key": self.selected_activity_key,
            "selected_activity_version": self.selected_activity_version,
            "selected_renderer_key": self.selected_renderer_key,
            "selected_renderer_version": self.selected_renderer_version,
        }


def route_workspace_intent(intent: WorkspaceIntent, context: WorkspaceAuthorityContext) -> WorkspaceExecutionDecision:
    """Select only exact registered capability contracts; this function never mutates Studio."""

    try:
        return _route_workspace_intent(intent, context)
    except Exception:
        # Chat success cannot depend on a future Workspace execution adapter.
        return _fallback("ROUTING_EXCEPTION")


def _route_workspace_intent(intent: WorkspaceIntent, context: WorkspaceAuthorityContext) -> WorkspaceExecutionDecision:
    active_scene_id = context.active_scene.scene_id if context.active_scene is not None else context.active_scene_id
    if intent.action.value == "NO_CHANGE":
        return _preserve(active_scene_id) if active_scene_id is not None else _no_change("NO_ACTIVE_SCENE")
    if intent.action.value == "CLOSE_ACTIVITY":
        return (
            WorkspaceExecutionDecision(WORKSPACE_EXECUTION_DECISION_VERSION, WorkspaceDecisionStatus.CLOSE_ACTIVE_SCENE, None, "ACTIVE_SCENE_IDENTIFIED", active_scene_id, None)
            if active_scene_id is not None
            else _no_change("NO_ACTIVE_SCENE")
        )
    if _active_scene_is_suitable(intent, context):
        return _preserve(active_scene_id)
    if not _references_are_authorized(intent, context):
        return _fallback("UNAUTHORIZED_SOURCE_REFERENCE")
    if intent.representation_need.value == "SOURCE" or intent.action.value == "FOCUS_SOURCE":
        source = _first_requested_source(intent)
        return _routed(WorkspaceExecutionMode.SOURCE_VIEW, "AUTHORIZED_SOURCE", source)
    profile = _current_profile(intent, context)
    if profile is None:
        return _fallback("KNOWN_CAPABILITY_UNAVAILABLE")
    if intent.representation_need.value == "ANNOTATION" or intent.action.value == "REQUEST_ANNOTATION":
        annotation = _annotation_candidate(profile, context)
        source = _first_requested_source(intent)
        if annotation is not None and source is not None:
            return _routed(WorkspaceExecutionMode.ANNOTATION, "ANNOTATION_CAPABILITY_AVAILABLE", source, profile=profile, renderer=annotation)
        return _fallback("ANNOTATION_CAPABILITY_UNAVAILABLE")
    candidate = _known_activity_candidate(intent, profile, context)
    if candidate is not None:
        activity, renderer = candidate
        return _routed(
            WorkspaceExecutionMode.KNOWN_INTERACTIVE if renderer.interactive else WorkspaceExecutionMode.KNOWN_VISUAL,
            "EXACT_KNOWN_CAPABILITY", None, profile=profile, activity=activity, renderer=renderer,
        )
    if intent.action.value == "REQUEST_CUSTOM_COMPOSE" or intent.representation_need.value == "CUSTOM_COMPOSITION":
        if profile.canvas_specialist_profile_key is not None:
            return _routed(WorkspaceExecutionMode.CUSTOM_COMPOSE, "CUSTOM_COMPOSE_ELIGIBLE", None, profile=profile)
        return _fallback("CUSTOM_COMPOSE_UNAVAILABLE")
    return _fallback("KNOWN_CAPABILITY_UNAVAILABLE")


def _references_are_authorized(intent: WorkspaceIntent, context: WorkspaceAuthorityContext) -> bool:
    requested = set(intent.source_references)
    if not requested:
        return intent.action.value not in {"FOCUS_SOURCE", "REQUEST_ANNOTATION"} and intent.representation_need.value not in {"SOURCE", "ANNOTATION"}
    authorized = set(context.authorized_source_references)
    if context.active_scene is not None:
        authorized.update(context.active_scene.source_references)
    return requested.issubset(authorized)


def _first_requested_source(intent: WorkspaceIntent) -> str | None:
    return intent.source_references[0] if intent.source_references else None


def _current_profile(intent: WorkspaceIntent, context: WorkspaceAuthorityContext) -> SubjectCapabilityProfile | None:
    if context.registry is None or intent.subject_key is None:
        return None
    profile_version = context.current_profile_versions.get(intent.subject_key)
    if profile_version is None:
        return None
    try:
        return context.registry.resolve_profile(intent.subject_key, profile_version)
    except SubjectCapabilityError:
        return None


def _active_scene_is_suitable(intent: WorkspaceIntent, context: WorkspaceAuthorityContext) -> bool:
    scene = context.active_scene
    if scene is None or context.registry is None:
        return False
    if intent.subject_key is not None and intent.subject_key != scene.subject_key:
        return False
    if intent.activity_hint is not None and intent.activity_hint != scene.activity_key:
        return False
    try:
        activity = context.registry.resolve_activity(scene.subject_key, scene.subject_profile_version, scene.activity_key, scene.activity_version)
        renderer = context.registry.resolve_renderer(scene.subject_key, scene.subject_profile_version, scene.renderer_key, scene.renderer_version)
    except SubjectCapabilityError:
        return False
    if activity.renderer_key != renderer.renderer_key or activity.renderer_version != renderer.renderer_version:
        return False
    return _renderer_matches_need(renderer, intent)


def _annotation_candidate(profile: SubjectCapabilityProfile, context: WorkspaceAuthorityContext) -> RendererContract | None:
    candidates = [renderer for renderer in profile.renderers if renderer.annotation_compatible]
    return candidates[0] if len(candidates) == 1 else None


def _known_activity_candidate(
    intent: WorkspaceIntent,
    profile: SubjectCapabilityProfile,
    context: WorkspaceAuthorityContext,
) -> tuple[ActivityContract, RendererContract] | None:
    candidates: list[tuple[ActivityContract, RendererContract]] = []
    for activity in profile.activities:
        if intent.activity_hint is None and activity.requires_explicit_hint:
            continue
        if intent.activity_hint is not None and intent.activity_hint != activity.activity_key:
            continue
        if not _activity_is_current(activity, profile, context):
            continue
        try:
            renderer = context.registry.resolve_renderer(profile.subject_key, profile.profile_version, activity.renderer_key, activity.renderer_version) if context.registry is not None else None
        except SubjectCapabilityError:
            renderer = None
        if renderer is not None and _renderer_matches_need(renderer, intent):
            candidates.append((activity, renderer))
    return candidates[0] if len(candidates) == 1 else None


def _activity_is_current(activity: ActivityContract, profile: SubjectCapabilityProfile, context: WorkspaceAuthorityContext) -> bool:
    candidates = [candidate for candidate in profile.activities if candidate.activity_key == activity.activity_key]
    if len(candidates) == 1:
        return True
    return context.current_activity_versions.get((profile.subject_key, profile.profile_version, activity.activity_key)) == activity.activity_version


def _renderer_matches_need(renderer: RendererContract, intent: WorkspaceIntent) -> bool:
    if intent.representation_need.value == "INTERACTIVE":
        return renderer.interactive
    if intent.representation_need.value == "VISUAL":
        return not renderer.interactive
    if intent.representation_need.value == "ANNOTATION":
        return renderer.annotation_compatible
    return True


def _preserve(scene_id: str) -> WorkspaceExecutionDecision:
    return WorkspaceExecutionDecision(WORKSPACE_EXECUTION_DECISION_VERSION, WorkspaceDecisionStatus.PRESERVE_ACTIVE_SCENE, None, "ACTIVE_SCENE_PRESERVED", scene_id, None)


def _no_change(reason_code: str) -> WorkspaceExecutionDecision:
    return WorkspaceExecutionDecision(WORKSPACE_EXECUTION_DECISION_VERSION, WorkspaceDecisionStatus.NO_CHANGE, None, reason_code, None, None)


def _fallback(reason_code: str) -> WorkspaceExecutionDecision:
    return WorkspaceExecutionDecision(WORKSPACE_EXECUTION_DECISION_VERSION, WorkspaceDecisionStatus.FALLBACK, None, reason_code, None, None)


def _routed(
    mode: WorkspaceExecutionMode,
    reason_code: str,
    source: str | None,
    *,
    profile: SubjectCapabilityProfile | None = None,
    activity: ActivityContract | None = None,
    renderer: RendererContract | None = None,
) -> WorkspaceExecutionDecision:
    return WorkspaceExecutionDecision(
        WORKSPACE_EXECUTION_DECISION_VERSION, WorkspaceDecisionStatus.ROUTED, mode, reason_code, None, source,
        None if profile is None else profile.subject_key,
        None if profile is None else profile.profile_version,
        None if activity is None else activity.activity_key,
        None if activity is None else activity.activity_version,
        None if renderer is None else renderer.renderer_key,
        None if renderer is None else renderer.renderer_version,
    )
