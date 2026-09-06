"""Unit contracts for the code-owned Studio Subject Capability Registry."""

from __future__ import annotations

import pytest

from services.studio.reducer import ReducerEvent, empty_snapshot, reduce_snapshot
from services.studio.subjects import production_subject_registry
from services.studio.subjects.contracts import (
    AccessibilityContract,
    ActivityActionContract,
    ActivityContract,
    InteractionPolicy,
    PayloadValidatorContract,
    ReducerContract,
    RendererContract,
    SubjectCapabilityProfile,
    ReducedMotionPolicy,
    SemanticValidationPolicy,
)
from services.studio.subjects.registry import SubjectCapabilityError, SubjectCapabilityRegistry
from services.studio.subjects.contracts import ValidationResult, ValidationStatus, ValidatorContract


def test_production_profiles_resolve_without_inferring_subject_from_locale() -> None:
    """Catch a registry that omits a production profile or couples subject to locale."""

    registry = production_subject_registry()

    assert registry.resolve_profile("MATH", "subject-profile-v1").subject_key == "MATH"
    assert registry.resolve_profile("SCIENCE", "subject-profile-v1").subject_key == "SCIENCE"
    assert registry.resolve_profile("ENGLISH", "subject-profile-v1").subject_key == "ENGLISH"
    assert registry.resolve_profile("ARABIC", "subject-profile-v1").subject_key == "ARABIC"
    assert registry.resolve_profile("MATH", "subject-profile-v1").activities == ()
    assert registry.resolve_profile("SCIENCE", "subject-profile-v1").activities == ()
    assert registry.resolve_profile("ENGLISH", "subject-profile-v1").activities == ()
    assert registry.resolve_profile("ARABIC", "subject-profile-v1").activities == ()
    assert registry.validate_locale("MATH", locale="ar", direction="rtl") == ("ar", "rtl")
    assert registry.validate_locale("ENGLISH", locale="ar", direction="rtl") == ("ar", "rtl")
    assert registry.validate_locale("ARABIC", locale="ar", direction="rtl") == ("ar", "rtl")


def _accessibility() -> AccessibilityContract:
    return AccessibilityContract(
        accessible_equivalent="button-controls",
        keyboard_policy="required",
        touch_policy="supported",
        direction_policy="bidirectional",
        mobile_fallback="text-controls",
        safe_fallback="safe-text",
        reduced_motion_policy=ReducedMotionPolicy.NO_MOTION,
    )


def _numeric_payload(payload: dict[str, object]) -> None:
    if set(payload) != {"value"} or not isinstance(payload["value"], int):
        raise ValueError("numeric fixture payload requires one integer value")


def _numeric_reducer(snapshot: dict[str, object], event: ReducerEvent) -> dict[str, object]:
    state = dict(snapshot["state_payload"])
    state["fixture_value"] = event.payload["value"]
    return {**snapshot, "latest_event_sequence": event.sequence, "state_payload": state}


def test_validation_result_v1_has_no_free_form_metadata_and_enforces_bounded_fields() -> None:
    """Catch a validator result that can smuggle arbitrary JSON into durable event history."""

    with pytest.raises(TypeError):
        ValidationResult(  # type: ignore[call-arg]
            ValidationStatus.INVALID,
            feedback_code="fixture-invalid",
            metadata={"unbounded": "metadata"},
        )
    with pytest.raises(ValueError, match="feedback"):
        ValidationResult(ValidationStatus.INVALID, feedback_code="x" * 129)
    with pytest.raises(ValueError, match="next action"):
        ValidationResult(
            ValidationStatus.INVALID,
            next_action_keys=tuple(f"fixture.action.{index}" for index in range(9)),
        )


def test_accessibility_rejects_unbounded_reduced_motion_policy() -> None:
    """Catch arbitrary reduced-motion text being accepted as a renderer contract."""

    with pytest.raises(ValueError, match="reduced-motion"):
        AccessibilityContract(
            accessible_equivalent="button-controls",
            keyboard_policy="required",
            touch_policy="supported",
            direction_policy="bidirectional",
            mobile_fallback="text-controls",
            safe_fallback="safe-text",
            reduced_motion_policy="anything the caller writes",
        )


def test_registry_resolves_action_key_independently_of_durable_event_kind() -> None:
    """Catch a registry that treats a renderer's action identity as the emitted event kind."""

    action = ActivityActionContract(
        action_key="fixture.numeric.submit_action",
        event_kind="fixture.numeric.step_submitted",
        event_schema_version="fixture-event-v1",
        payload_schema_version="fixture-payload-v1",
        payload_validator_key="numeric-payload",
        interaction_policy=InteractionPolicy.RECORD_ONLY,
        semantic_validation_policy=SemanticValidationPolicy.NONE,
    )
    profile = SubjectCapabilityProfile(
        subject_key="ACTION_FIXTURE",
        profile_version="fixture-profile-v1",
        supported_grade_scope=(),
        concept_namespace="fixture.actions",
        tutor_guidance_fragment="fixture-only",
        grounding_policy_key="none",
        locale_policy_key="subject-independent",
        deterministic_fallback="safe-text",
        canvas_specialist_profile_key=None,
        renderers=(
            RendererContract(
                renderer_key="fixture-renderer",
                renderer_version="fixture-renderer-v1",
                subject_key="ACTION_FIXTURE",
                supported_activity_keys=("action-fixture",),
                scene_input_schema_version="fixture-payload-v1",
                interactive=True,
                supported_action_keys=(action.action_key,),
                required_validator_keys=(),
                state_adapter_key="fixture-adapter-v1",
                accessibility=_accessibility(),
                source_view_compatible=False,
                annotation_compatible=False,
                reconstruction_compatible=False,
                implementation_status="TEST_ONLY",
            ),
        ),
        payload_validators=(PayloadValidatorContract("numeric-payload", "fixture-payload-v1", _numeric_payload),),
        reducers=(ReducerContract("numeric-reducer", "fixture-reducer-v1", _numeric_reducer),),
        activities=(
            ActivityContract(
                activity_key="action-fixture",
                activity_version="fixture-activity-v1",
                subject_key="ACTION_FIXTURE",
                concept_namespace="fixture.actions",
                renderer_key="fixture-renderer",
                renderer_version="fixture-renderer-v1",
                initial_scene_payload_schema_version="fixture-payload-v1",
                initial_scene_payload_validator_key="numeric-payload",
                actions=(action,),
                completion_semantics="fixture",
                immediate_feedback_policy="bounded",
                support_action_keys=(),
                fallback="safe-text",
                accessibility=_accessibility(),
                reducer_key="numeric-reducer",
                reducer_version="fixture-reducer-v1",
            ),
        ),
    )

    registry = SubjectCapabilityRegistry((profile,))
    resolved, validation = registry.validate_subject_event(
        subject_key="ACTION_FIXTURE",
        subject_profile_version="fixture-profile-v1",
        activity_key="action-fixture",
        activity_version="fixture-activity-v1",
        action_key="fixture.numeric.submit_action",
        payload_schema_version="fixture-payload-v1",
        payload={"value": 4},
    )

    assert resolved.action_key == "fixture.numeric.submit_action"
    assert resolved.event_kind == "fixture.numeric.step_submitted"
    assert validation is None


def fixture_registry(*, subject_key: str = "FIXTURE_NUMERIC") -> SubjectCapabilityRegistry:
    activity_key = "numeric-fixture"
    renderer_key = "fixture-renderer"
    schema_version = "fixture-payload-v1"
    actions = (
        ActivityActionContract(
            action_key="fixture.numeric.record",
            event_kind="fixture.numeric.record",
            event_schema_version="fixture-event-v1",
            payload_schema_version=schema_version,
            payload_validator_key="numeric-payload",
            interaction_policy=InteractionPolicy.RECORD_ONLY,
            semantic_validation_policy=SemanticValidationPolicy.NONE,
        ),
        ActivityActionContract(
            action_key="fixture.numeric.submit",
            event_kind="fixture.numeric.submit",
            event_schema_version="fixture-event-v1",
            payload_schema_version=schema_version,
            payload_validator_key="numeric-payload",
            interaction_policy=InteractionPolicy.TUTOR_TRIGGERING,
            semantic_validation_policy=SemanticValidationPolicy.NONE,
            interaction_kind="fixture-submit",
        ),
    )
    profile = SubjectCapabilityProfile(
        subject_key=subject_key,
        profile_version="fixture-profile-v1",
        supported_grade_scope=("fixture",),
        concept_namespace="fixture.numeric",
        tutor_guidance_fragment="fixture-only",
        grounding_policy_key="none",
        locale_policy_key="subject-independent",
        deterministic_fallback="safe-text",
        canvas_specialist_profile_key=None,
        renderers=(
            RendererContract(
                renderer_key=renderer_key,
                renderer_version="fixture-renderer-v1",
                subject_key=subject_key,
                supported_activity_keys=(activity_key,),
                scene_input_schema_version=schema_version,
                interactive=True,
                supported_action_keys=tuple(action.action_key for action in actions),
                required_validator_keys=(),
                state_adapter_key="fixture-adapter-v1",
                accessibility=_accessibility(),
                source_view_compatible=False,
                annotation_compatible=False,
                reconstruction_compatible=False,
                implementation_status="TEST_ONLY",
            ),
        ),
        payload_validators=(
            PayloadValidatorContract("numeric-payload", schema_version, _numeric_payload),
        ),
        reducers=(ReducerContract("numeric-reducer", "fixture-reducer-v1", _numeric_reducer),),
        activities=(
            ActivityContract(
                activity_key=activity_key,
                activity_version="fixture-activity-v1",
                subject_key=subject_key,
                concept_namespace="fixture.numeric",
                renderer_key=renderer_key,
                renderer_version="fixture-renderer-v1",
                initial_scene_payload_schema_version=schema_version,
                initial_scene_payload_validator_key="numeric-payload",
                actions=actions,
                completion_semantics="fixture submit",
                immediate_feedback_policy="bounded",
                support_action_keys=(),
                fallback="safe-text",
                accessibility=_accessibility(),
                reducer_key="numeric-reducer",
                reducer_version="fixture-reducer-v1",
            ),
        ),
    )
    return SubjectCapabilityRegistry((profile,))


def test_fixture_subject_registers_and_reduces_exact_typed_action_deterministically() -> None:
    """Catch generic event acceptance, a wrong reducer, or mutable subject-specific core behavior."""

    registry = fixture_registry(subject_key="GEOGRAPHY_FIXTURE")
    event = ReducerEvent(
        id=__import__("uuid").uuid4(),
        sequence=1,
        event_kind="fixture.numeric.record",
        action_key="fixture.numeric.record",
        event_schema_version="fixture-event-v1",
        actor="STUDENT",
        scene_id=None,
        base_scene_version=None,
        resulting_scene_version=None,
        subject_key="GEOGRAPHY_FIXTURE",
        subject_profile_version="fixture-profile-v1",
        activity_key="numeric-fixture",
        activity_contract_version="fixture-activity-v1",
        payload_schema_version="fixture-payload-v1",
        payload={"value": 4},
    )

    assert reduce_snapshot(empty_snapshot(), event, subject_registry=registry)["state_payload"] == {
        "fixture_value": 4
    }
    assert reduce_snapshot(empty_snapshot(), event, subject_registry=registry) == reduce_snapshot(
        empty_snapshot(), event, subject_registry=registry
    )

    from dataclasses import replace
    from uuid import uuid4

    scene_id = uuid4()
    scene_event = replace(event, scene_id=scene_id, base_scene_version=2, resulting_scene_version=3)
    with pytest.raises(ValueError, match="current Scene"):
        reduce_snapshot(empty_snapshot(), scene_event, subject_registry=registry)
    active = {**empty_snapshot(), "current_scene_id": scene_id, "current_scene_version": 2}
    reduced = reduce_snapshot(active, scene_event, subject_registry=registry)
    assert reduced["current_scene_id"] == scene_id
    assert reduced["current_scene_version"] == 3
    assert active["current_scene_version"] == 2
    for invalid in (replace(scene_event, base_scene_version=1), replace(scene_event, resulting_scene_version=None)):
        with pytest.raises(ValueError, match="version"):
            reduce_snapshot(active, invalid, subject_registry=registry)


def test_registry_rejects_unknown_version_duplicate_profile_and_untyped_fixture_event() -> None:
    """Catch silent latest-version fallback, duplicate registration, or untyped event acceptance."""

    registry = fixture_registry()

    with pytest.raises(SubjectCapabilityError, match="Unsupported Activity contract"):
        registry.resolve_activity("FIXTURE_NUMERIC", "fixture-profile-v1", "numeric-fixture", "fixture-activity-v2")
    with pytest.raises(SubjectCapabilityError, match="Duplicate Subject profile"):
        SubjectCapabilityRegistry(
            (
                registry.resolve_profile("FIXTURE_NUMERIC", "fixture-profile-v1"),
                registry.resolve_profile("FIXTURE_NUMERIC", "fixture-profile-v1"),
            )
        )


def test_profile_scoped_activity_and_exact_versioned_validator_are_required() -> None:
    """Catch resolution that silently uses another profile or skips semantic validation."""

    registry = fixture_registry()
    assert registry.validate_scene(
        subject_key="FIXTURE_NUMERIC",
        subject_profile_version="fixture-profile-v1",
        activity_key="numeric-fixture",
        activity_version="fixture-activity-v1",
        renderer_key="fixture-renderer",
        renderer_version="fixture-renderer-v1",
        payload_schema_version="fixture-payload-v1",
        seed_payload={"value": 1},
        locale="ar",
        direction="rtl",
    ).subject_key == "FIXTURE_NUMERIC"
    with pytest.raises(SubjectCapabilityError, match="Unsupported Activity action contract"):
        registry.validate_subject_event(
            subject_key="FIXTURE_NUMERIC",
            subject_profile_version="fixture-profile-v1",
            activity_key="numeric-fixture",
            activity_version="fixture-activity-v1",
            action_key="fixture.numeric.untyped",
            payload_schema_version="fixture-payload-v1",
            payload={"value": 4},
        )
