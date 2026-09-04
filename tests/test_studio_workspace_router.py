"""Runtime-02 deterministic routing tests using fixture-only capabilities."""

from __future__ import annotations

from services.studio.subjects.contracts import (
    AccessibilityContract,
    ActivityActionContract,
    ActivityContract,
    InteractionPolicy,
    PayloadValidatorContract,
    ReducerContract,
    RendererContract,
    ReducedMotionPolicy,
    SemanticValidationPolicy,
    SubjectCapabilityProfile,
)
from services.studio.subjects.registry import SubjectCapabilityRegistry
from services.studio.workspace_intent import WorkspaceIntent


def _validate(_: dict[str, object]) -> None:
    return None


def _reduce(snapshot: dict[str, object], _: object) -> dict[str, object]:
    return snapshot


def _accessibility() -> AccessibilityContract:
    return AccessibilityContract(
        accessible_equivalent="fixture accessible equivalent",
        keyboard_policy="fixture keyboard",
        touch_policy="fixture touch",
        direction_policy="auto",
        mobile_fallback="fixture mobile",
        safe_fallback="fixture safe fallback",
        reduced_motion_policy=ReducedMotionPolicy.NO_MOTION,
    )


def _fixture_registry(*, custom_compose: bool = False) -> SubjectCapabilityRegistry:
    actions = (
        ActivityActionContract(
            action_key="SUBMIT", event_kind="fixture.submitted", event_schema_version="fixture-event-v1",
            payload_schema_version="fixture-payload-v1", payload_validator_key="fixture-payload",
            interaction_policy=InteractionPolicy.RECORD_ONLY,
            semantic_validation_policy=SemanticValidationPolicy.NONE,
        ),
    )
    def activity(key: str, renderer_key: str) -> ActivityContract:
        return ActivityContract(
            activity_key=key, activity_version="fixture-activity-v1", subject_key="FIXTURE",
            concept_namespace="fixture", renderer_key=renderer_key, renderer_version="fixture-renderer-v1",
            initial_scene_payload_schema_version="fixture-payload-v1", initial_scene_payload_validator_key="fixture-payload",
            actions=actions, completion_semantics="fixture", immediate_feedback_policy="fixture",
            support_action_keys=(), fallback="fixture", accessibility=_accessibility(),
            reducer_key="fixture-reducer", reducer_version="fixture-reducer-v1",
        )
    profile = SubjectCapabilityProfile(
        subject_key="FIXTURE", profile_version="fixture-profile-v1", supported_grade_scope=(),
        concept_namespace="fixture", tutor_guidance_fragment="fixture guidance", grounding_policy_key="fixture",
        locale_policy_key="fixture", deterministic_fallback="fixture", canvas_specialist_profile_key=("fixture-specialist" if custom_compose else None),
        renderers=(
            RendererContract("visual", "fixture-renderer-v1", "FIXTURE", ("visual_activity",), "fixture-payload-v1", False, ("SUBMIT",), (), "fixture", _accessibility(), False, False, False, "TEST_ONLY"),
            RendererContract("interactive", "fixture-renderer-v1", "FIXTURE", ("interactive_activity",), "fixture-payload-v1", True, ("SUBMIT",), (), "fixture", _accessibility(), False, False, False, "TEST_ONLY"),
            RendererContract("annotation", "fixture-renderer-v1", "FIXTURE", ("annotation_activity",), "fixture-payload-v1", False, ("SUBMIT",), (), "fixture", _accessibility(), False, True, False, "TEST_ONLY"),
        ),
        activities=(activity("visual_activity", "visual"), activity("interactive_activity", "interactive"), activity("annotation_activity", "annotation")),
        payload_validators=(PayloadValidatorContract("fixture-payload", "fixture-payload-v1", _validate),),
        reducers=(ReducerContract("fixture-reducer", "fixture-reducer-v1", _reduce),),
    )
    return SubjectCapabilityRegistry((profile,))


def _intent(**updates: object) -> WorkspaceIntent:
    value: dict[str, object] = {
        "version": "workspace-intent-v1", "action": "OPEN_ACTIVITY", "subject_key": "FIXTURE",
        "concept_keys": [], "learning_goal": "Use a helpful representation.", "activity_hint": None,
        "representation_need": "VISUAL", "expected_student_response_mode": "WORKSPACE",
        "presentation_sequence": "PARALLEL", "source_references": [], "safe_text_fallback": "Let's work through this together.",
    }
    value.update(updates)
    return WorkspaceIntent.model_validate(value)


def test_router_selects_exact_fixture_visual_before_custom_compose() -> None:
    """A suitable approved capability wins over a Tutor custom-compose preference."""

    from services.studio.router import (  # noqa: PLC0415 - RED contract
        WorkspaceAuthorityContext,
        WorkspaceExecutionMode,
        route_workspace_intent,
    )

    decision = route_workspace_intent(
        _intent(action="REQUEST_CUSTOM_COMPOSE", activity_hint="visual_activity"),
        WorkspaceAuthorityContext(
            registry=_fixture_registry(custom_compose=True),
            current_profile_versions={"FIXTURE": "fixture-profile-v1"},
        ),
    )

    assert decision.mode is WorkspaceExecutionMode.KNOWN_VISUAL
    assert decision.selected_activity_key == "visual_activity"


def test_router_uses_authorized_source_and_annotation_before_known_activity() -> None:
    """Source and annotation routes are explicit and cannot use invented references."""

    from services.studio.router import WorkspaceAuthorityContext, WorkspaceExecutionMode, WorkspaceDecisionStatus, route_workspace_intent

    context = WorkspaceAuthorityContext(
        registry=_fixture_registry(), current_profile_versions={"FIXTURE": "fixture-profile-v1"},
        authorized_source_references=("source-1",),
    )

    source = route_workspace_intent(_intent(action="FOCUS_SOURCE", representation_need="SOURCE", source_references=["source-1"]), context)
    annotation = route_workspace_intent(_intent(action="REQUEST_ANNOTATION", representation_need="ANNOTATION", source_references=["source-1"]), context)
    denied = route_workspace_intent(_intent(action="FOCUS_SOURCE", representation_need="SOURCE", source_references=["invented"]), context)

    assert source.mode is WorkspaceExecutionMode.SOURCE_VIEW
    assert annotation.mode is WorkspaceExecutionMode.ANNOTATION
    assert denied.status is WorkspaceDecisionStatus.FALLBACK
    assert denied.reason_code == "UNAUTHORIZED_SOURCE_REFERENCE"


def test_router_preserves_a_suitable_active_scene_before_source_routing() -> None:
    """An already-suitable Scene wins; source authorization governs only a source route."""

    from services.studio.router import (  # noqa: PLC0415 - RED contract
        ActiveSceneCapability,
        WorkspaceAuthorityContext,
        WorkspaceDecisionStatus,
        WorkspaceExecutionMode,
        route_workspace_intent,
    )

    context = WorkspaceAuthorityContext(
        registry=_fixture_registry(),
        current_profile_versions={"FIXTURE": "fixture-profile-v1"},
        authorized_source_references=("source-1",),
        active_scene=ActiveSceneCapability(
            scene_id="scene-1",
            subject_key="FIXTURE",
            subject_profile_version="fixture-profile-v1",
            activity_key="visual_activity",
            activity_version="fixture-activity-v1",
            renderer_key="visual",
            renderer_version="fixture-renderer-v1",
        ),
    )

    suitable = route_workspace_intent(
        _intent(action="FOCUS_SOURCE", representation_need="SOURCE", source_references=["unneeded-source"]), context
    )
    unsuitable = route_workspace_intent(
        _intent(action="FOCUS_SOURCE", subject_key="SCIENCE", representation_need="SOURCE", source_references=["source-1"]), context
    )
    unauthorized_without_a_suitable_scene = route_workspace_intent(
        _intent(action="FOCUS_SOURCE", subject_key="SCIENCE", representation_need="SOURCE", source_references=["invented"]), context
    )

    assert suitable.status is WorkspaceDecisionStatus.PRESERVE_ACTIVE_SCENE
    assert suitable.target_scene_id == "scene-1"
    assert unsuitable.mode is WorkspaceExecutionMode.SOURCE_VIEW
    assert unauthorized_without_a_suitable_scene.status is WorkspaceDecisionStatus.FALLBACK
    assert unauthorized_without_a_suitable_scene.reason_code == "UNAUTHORIZED_SOURCE_REFERENCE"


def test_router_selects_interactive_and_only_then_custom_compose() -> None:
    """Known exact capabilities are preferred; fixture custom eligibility remains decision-only."""

    from services.studio.router import WorkspaceAuthorityContext, WorkspaceExecutionMode, route_workspace_intent

    context = WorkspaceAuthorityContext(
        registry=_fixture_registry(custom_compose=True), current_profile_versions={"FIXTURE": "fixture-profile-v1"},
    )
    interactive = route_workspace_intent(_intent(activity_hint="interactive_activity", representation_need="INTERACTIVE"), context)
    custom = route_workspace_intent(_intent(action="REQUEST_CUSTOM_COMPOSE", representation_need="CUSTOM_COMPOSITION"), context)

    assert interactive.mode is WorkspaceExecutionMode.KNOWN_INTERACTIVE
    assert custom.mode is WorkspaceExecutionMode.CUSTOM_COMPOSE
