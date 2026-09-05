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

    assert TUTOR_OUTPUT_RESPONSE_SCHEMA["name"] == "tutor_turn_v9"
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
    assert value["authorized_source_references"] == ["retrieval-1"]
    assert "renderers" not in value
