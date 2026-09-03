"""Typed contract coverage for STUDIO-RUNTIME-01 model-facing Studio context."""

from __future__ import annotations

from uuid import uuid4


def test_studio_tutor_context_exposes_snapshot_and_ordered_semantic_events() -> None:
    """Tutor receives compact semantic Workspace state, never ORM row objects."""

    from services.studio.tutor_context import (  # noqa: PLC0415 - RED-phase import contract
        StudioTutorEventContext,
        StudioTutorWorkspaceContext,
    )

    runtime_id = uuid4()
    context = StudioTutorWorkspaceContext(
        runtime_id=runtime_id,
        snapshot_schema_version="studio-snapshot-v1",
        through_sequence=4,
        snapshot_sequence=4,
        current_scene_id=None,
        current_scene_version=None,
        active_subject_key="MATH",
        active_activity_key=None,
        state_payload={"scene": "accepted"},
        unseen_events=(
            StudioTutorEventContext(
                sequence=4,
                actor="STUDENT",
                event_kind="fixture.step_submitted",
                action_key="SUBMIT_STEP",
                subject_key="MATH",
                activity_key="fixture_activity",
                base_scene_version=1,
                resulting_scene_version=2,
                payload_schema_version="fixture-action-v1",
                payload={"action": {"answer": "4"}, "validation": {"status": "INVALID"}},
            ),
        ),
        observation_id=uuid4(),
    )

    assert context.as_model_payload() == {
        "schema_version": "studio-tutor-context-v1",
        "through_sequence": 4,
        "snapshot": {
            "schema_version": "studio-snapshot-v1",
            "sequence": 4,
            "current_scene_id": None,
            "current_scene_version": None,
            "active_subject_key": "MATH",
            "active_activity_key": None,
            "state": {"scene": "accepted"},
        },
        "unseen_events": [
            {
                "sequence": 4,
                "actor": "STUDENT",
                "event_kind": "fixture.step_submitted",
                "action_key": "SUBMIT_STEP",
                "subject_key": "MATH",
                "activity_key": "fixture_activity",
                "base_scene_version": 1,
                "resulting_scene_version": 2,
                "payload_schema_version": "fixture-action-v1",
                "payload": {"action": {"answer": "4"}, "validation": {"status": "INVALID"}},
            }
        ],
    }


def test_tutor_model_payload_includes_typed_studio_workspace_context() -> None:
    """Studio is additive deterministic input to the existing primary Tutor call."""

    from services.studio.tutor_context import StudioTutorWorkspaceContext
    from services.tutor.runtime import build_tutor_model_payload

    studio = StudioTutorWorkspaceContext(
        runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=0,
        snapshot_sequence=0, current_scene_id=None, current_scene_version=None,
        active_subject_key=None, active_activity_key=None, state_payload={}, unseen_events=(), observation_id=None,
    )

    payload = build_tutor_model_payload(question="Can you help me?", studio_context=studio)

    assert "Studio Workspace Context" in str(payload["input"])
    assert '"through_sequence": 0' in str(payload["input"])
