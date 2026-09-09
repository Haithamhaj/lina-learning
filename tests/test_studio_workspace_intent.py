"""Contract tests for the bounded Runtime-02 WorkspaceIntent."""

from __future__ import annotations

import pytest
from uuid import uuid4


def test_workspace_intent_v1_accepts_null_and_bounded_educational_need() -> None:
    """A Tutor may request an educational need, never implementation authority."""

    from services.studio.workspace_intent import (  # noqa: PLC0415 - RED contract
        WorkspaceIntent,
        parse_workspace_intent,
    )

    assert parse_workspace_intent(None) is None
    intent = WorkspaceIntent.model_validate(
        {
            "version": "workspace-intent-v1",
            "action": "OPEN_ACTIVITY",
            "subject_key": "MATH",
            "concept_keys": ["equivalent_fractions"],
            "learning_goal": "Compare equivalent fractions.",
            "activity_hint": "fraction bars",
            "representation_need": "INTERACTIVE",
            "expected_student_response_mode": "WORKSPACE",
            "presentation_sequence": "PARALLEL",
            "source_references": [],
            "safe_text_fallback": "Let's compare the two fractions together.",
        }
    )

    assert intent.action.value == "OPEN_ACTIVITY"
    with pytest.raises(ValueError):
        WorkspaceIntent.model_validate({**intent.model_dump(), "renderer_key": "number_line"})


def test_tutor_output_requires_nullable_workspace_intent_with_its_own_schema_version() -> None:
    """Structured Tutor output must carry the optional request without reinterpreting v8."""

    from services.tutor.candidate_events import (  # noqa: PLC0415 - RED contract
        TUTOR_OUTPUT_JSON_SCHEMA,
        TUTOR_OUTPUT_RESPONSE_SCHEMA,
    )

    assert TUTOR_OUTPUT_RESPONSE_SCHEMA["name"] == "tutor_turn_v10"
    assert "workspace_intent" in TUTOR_OUTPUT_JSON_SCHEMA["required"]
    schema = TUTOR_OUTPUT_JSON_SCHEMA["properties"]["workspace_intent"]
    assert schema["anyOf"][0]["additionalProperties"] is False
    assert schema["anyOf"][0]["properties"]["version"]["enum"] == ["workspace-intent-v1"]
    assert schema["anyOf"][1] == {"type": "null"}


def test_router_preserves_an_active_scene_for_no_change_without_state_mutation() -> None:
    """NO_CHANGE is a bounded routing decision, not a synthetic Studio Event."""

    from services.studio.router import (  # noqa: PLC0415 - RED contract
        WorkspaceAuthorityContext,
        WorkspaceDecisionStatus,
        route_workspace_intent,
    )
    from services.studio.workspace_intent import WorkspaceIntent

    scene_id = "fdf1942d-765d-4a1a-aa30-8d6c5b58afaa"
    decision = route_workspace_intent(
        WorkspaceIntent.model_validate(
            {
                "version": "workspace-intent-v1", "action": "NO_CHANGE", "subject_key": "MATH",
                "concept_keys": [], "learning_goal": None, "activity_hint": None,
                "representation_need": "NONE", "expected_student_response_mode": "NONE",
                "presentation_sequence": "TEXT_FIRST", "source_references": [], "safe_text_fallback": None,
            }
        ),
        WorkspaceAuthorityContext(active_scene_id=scene_id, active_subject_key="MATH"),
    )

    assert decision.status is WorkspaceDecisionStatus.PRESERVE_ACTIVE_SCENE
    assert decision.target_scene_id == scene_id
    assert decision.requires_state_mutation is False


def test_production_workspace_capability_context_is_honest_and_compact() -> None:
    """The Tutor sees compact current Make-Ten availability, not a registry dump."""

    from services.studio.workspace_capabilities import build_workspace_capability_context  # noqa: PLC0415 - RED contract
    from services.studio.tutor_context import StudioTutorWorkspaceContext

    value = build_workspace_capability_context(
        StudioTutorWorkspaceContext(
            runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=0,
            snapshot_sequence=0, current_scene_id=None, current_scene_version=None,
            active_subject_key="MATH", active_activity_key=None, state_payload={}, unseen_events=(), observation_id=None,
        ),
        authorized_source_references=("retrieval-1",),
    ).as_model_payload()

    assert value["known_workspace_capabilities_available"] is True
    assert value["authorized_source_references"][0] == "retrieval-1"
    assert set(value["authorized_source_references"][1:]) == {p['source_ref'] for p in value['authored_problem_sources']}
    assert len([p for p in value['authored_problem_sources'] if p['activity_hint']=='decimal_number_line']) == 11
    assert len([p for p in value['authored_problem_sources'] if p['activity_hint']=='decimal_place_value']) == 12
    assert "renderers" not in value


@pytest.mark.parametrize("broad_subject", [None, "GENERAL_KNOWLEDGE", "OTHER"])
def test_open_workspace_without_a_primary_subject_advertises_no_subject_drifting_composition(
    broad_subject: str | None,
) -> None:
    """A general Canvas order must not silently manufacture a Math or Science identity."""

    from services.studio.workspace_capabilities import build_workspace_capability_context
    from services.studio.tutor_context import StudioTutorWorkspaceContext

    value = build_workspace_capability_context(
        StudioTutorWorkspaceContext(
            runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=0,
            snapshot_sequence=0, current_scene_id=None, current_scene_version=None,
            active_subject_key=None, active_activity_key=None, state_payload={}, unseen_events=(), observation_id=None,
        ),
        authorized_source_references=(),
        current_subject_key=broad_subject,
    ).as_model_payload()

    assert value["subject_key"] == broad_subject
    assert value["known_workspace_capabilities_available"] is False
    assert value["custom_compose_potentially_eligible"] is False
    assert value["eligible_custom_composition_patterns"] == []
    assert value["custom_composition_constraints"] == {}
    assert value["authored_problem_sources"] == []


@pytest.mark.parametrize(
    ("subject_key", "expected_patterns"),
    [
        ("MATH", ["SPATIAL_MANIPULATION", "MATH_VISUALIZATION", "MATH_INPUT"]),
        ("SCIENCE", ["PROCESS"]),
        ("ENGLISH", []),
        ("ARABIC", []),
    ],
)
def test_known_primary_subject_exposes_only_matching_custom_composition_patterns(
    subject_key: str,
    expected_patterns: list[str],
) -> None:
    """A known subject narrows exact composition capability without becoming a blanket gate."""

    from services.studio.workspace_capabilities import build_workspace_capability_context
    from services.studio.tutor_context import StudioTutorWorkspaceContext

    value = build_workspace_capability_context(
        StudioTutorWorkspaceContext(
            runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=0,
            snapshot_sequence=0, current_scene_id=None, current_scene_version=None,
            active_subject_key=subject_key, active_activity_key=None, state_payload={}, unseen_events=(), observation_id=None,
        ),
        authorized_source_references=(),
    ).as_model_payload()

    assert value["subject_key"] == subject_key
    assert value["eligible_custom_composition_patterns"] == expected_patterns
    assert value["custom_compose_potentially_eligible"] is bool(expected_patterns)
    assert list(value["custom_composition_constraints"]) == expected_patterns


@pytest.mark.parametrize(
    ("known_subject", "matching_pattern"),
    [("MATH", "MATH_VISUALIZATION"), ("SCIENCE", "PROCESS")],
)
def test_subject_becoming_known_preserves_a_matching_production_composition(
    known_subject: str,
    matching_pattern: str,
) -> None:
    """Classification may narrow candidates but must not remove an exact production fit."""

    from services.studio.workspace_capabilities import build_workspace_capability_context
    from services.studio.tutor_context import StudioTutorWorkspaceContext

    def context(subject_key: str | None) -> dict[str, object]:
        return build_workspace_capability_context(
            StudioTutorWorkspaceContext(
                runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=0,
                snapshot_sequence=0, current_scene_id=None, current_scene_version=None,
                active_subject_key=subject_key, active_activity_key=None, state_payload={}, unseen_events=(), observation_id=None,
            ),
            authorized_source_references=(),
        ).as_model_payload()

    before = context(None)
    after = context(known_subject)

    assert before["eligible_custom_composition_patterns"] == []
    assert matching_pattern in after["eligible_custom_composition_patterns"]


def test_active_resolved_scene_keeps_its_authoritative_subject_capabilities() -> None:
    """Broad or stale Runtime labels cannot reclassify an already valid Scene."""

    from services.studio.workspace_capabilities import build_workspace_capability_context
    from services.studio.tutor_context import StudioTutorSceneCapability, StudioTutorWorkspaceContext

    scene_id = uuid4()
    value = build_workspace_capability_context(
        StudioTutorWorkspaceContext(
            runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=1,
            snapshot_sequence=1, current_scene_id=scene_id, current_scene_version=2,
            active_subject_key="SCIENCE", active_activity_key="stale-process", state_payload={}, unseen_events=(), observation_id=None,
            current_scene_capability=StudioTutorSceneCapability(
                scene_id=scene_id, subject_key="MATH", subject_profile_version="canvas-production-profile-v1",
                activity_key="canvas_math_visualization", activity_version="canvas-math-visualization-activity-v1",
                renderer_key="canvas-coordinate-construction", renderer_version="canvas-coordinate-construction-renderer-v1",
                allowed_action_keys=("PLACE_POINT", "SUBMIT_CONSTRUCTION"), source_references=(),
            ),
        ),
        current_subject_key="GENERAL_KNOWLEDGE",
        authorized_source_references=(),
    ).as_model_payload()

    assert value["subject_key"] == "MATH"
    assert value["eligible_custom_composition_patterns"] == [
        "SPATIAL_MANIPULATION", "MATH_VISUALIZATION", "MATH_INPUT",
    ]


def test_custom_composition_context_exposes_exact_academic_bounds_not_renderer_details() -> None:
    """The Tutor can reject an out-of-range point before composition without seeing implementation IDs."""

    from services.studio.workspace_capabilities import build_workspace_capability_context
    from services.studio.tutor_context import StudioTutorWorkspaceContext

    def constraints(subject_key: str) -> dict[str, object]:
        value = build_workspace_capability_context(
            StudioTutorWorkspaceContext(
                runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=0,
                snapshot_sequence=0, current_scene_id=None, current_scene_version=None,
                active_subject_key=subject_key, active_activity_key=None, state_payload={}, unseen_events=(), observation_id=None,
            ),
            authorized_source_references=(),
        ).as_model_payload()
        return value["custom_composition_constraints"]

    assert constraints("MATH")["MATH_VISUALIZATION"] == {
        "construction_family": "CARTESIAN_POINT",
        "coordinate_bounds": [-10, 10],
        "point_count": 1,
    }
    assert constraints("SCIENCE")["PROCESS"] == {
        "topologies": ["SEQUENCE", "CYCLE"],
        "stage_count": [2, 8],
    }


@pytest.mark.parametrize("studio_subject", ["ENGLISH", "ARABIC"])
def test_primary_studio_subject_outranks_its_broader_language_arts_scope(
    studio_subject: str,
) -> None:
    """Broad Subject guides semantics; it must not masquerade as a Studio capability key."""

    from services.studio.workspace_capabilities import build_workspace_capability_context
    from services.studio.tutor_context import StudioTutorWorkspaceContext

    value = build_workspace_capability_context(
        StudioTutorWorkspaceContext(
            runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=0,
            snapshot_sequence=0, current_scene_id=None, current_scene_version=None,
            active_subject_key=studio_subject, active_activity_key=None, state_payload={}, unseen_events=(), observation_id=None,
        ),
        current_subject_key="LANGUAGE_ARTS",
        authorized_source_references=(),
    ).as_model_payload()

    assert value["subject_key"] == studio_subject
    assert value["eligible_custom_composition_patterns"] == []
    assert value["custom_compose_potentially_eligible"] is False
