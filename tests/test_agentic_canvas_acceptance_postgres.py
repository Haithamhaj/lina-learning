"""Acceptance contracts for Tutor-led Agentic Canvas settlement and continuity."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import pytest
from test_agentic_canvas_lifecycle_postgres import factory  # noqa: F401

from services.platform.db import models as m
from services.studio.agent.admission import admit_agentic_canvas_brief
from services.studio.agentic_canvas import AgenticCanvasSceneV1
from services.studio.contracts import AppendStudioEventCommand, StudioActor
from services.studio.process_production_acceptance import (
    accept_completed_canvas_run,
    agentic_scene_contract,
)
from services.studio.service import StudioStateService
from services.studio.tutor_context import select_studio_tutor_context


def _brief(*, subject: str, locale: str = "en", direction: str = "ltr") -> dict[str, object]:
    return {
        "version": "canvas-brief-v1",
        "subject_key": subject,
        "objective": "Represent the relationship so the learner can inspect it.",
        "student_request": "Help me understand this visually.",
        "requested_representation": "Use a bounded educational representation.",
        "facts": ["The representation must preserve the supplied relationship."],
        "relations": [],
        "quantities": [],
        "desired_student_action": "Inspect and select a named element.",
        "must_not_imply": [],
        "source_references": [],
        "locale": locale,
        "direction": direction,
    }


def _scene(*, subject: str, block_type: str, element_count: int = 2) -> dict[str, object]:
    common: dict[str, object] = {
        "block_id": "generated-block",
        "type": block_type,
        "meaning": "A runtime-generated relationship with named semantic elements.",
        "title": "Explore the relationship",
        "accessibility": {"text_equivalent": "Named elements in their educational relationship.", "aria_label": None},
        "allowed_actions": ["SELECT"],
        "elements": [
            {"id": f"element-{index}", "label": f"Element {index}", "current_value": str(index)}
            for index in range(element_count)
        ],
    }
    subtype = {
        "MATH_BOARD": {"board_kind": "NUMBER_LINE", "axis_min": "0", "axis_max": "1"},
        "SCENE_2D": {"viewport_width_units": 100, "viewport_height_units": 100},
        "DIAGRAM": {"topology": "SEQUENCE", "layout": "AUTO"},
        "TEXT_INTERACTION": {"interaction_family": "ORDERING"},
        "MATH_INPUT": {"notation": "LATEX"},
    }[block_type]
    return {
        "version": "agentic-canvas-scene-v1",
        "objective": "Represent the relationship so the learner can inspect it.",
        "subject_key": subject,
        "blocks": [{**common, **subtype}],
    }


@pytest.mark.parametrize(
    ("subject", "block_type", "locale", "direction", "element_count"),
    [
        ("MATH", "MATH_BOARD", "en", "ltr", 2),
        ("PHYSICS", "DIAGRAM", "en", "ltr", 3),
        ("SCIENCE", "DIAGRAM", "en", "ltr", 6),
        ("ARABIC", "TEXT_INTERACTION", "ar", "rtl", 5),
        ("ENGLISH", "TEXT_INTERACTION", "en", "ltr", 5),
        ("SCIENCE", "SCENE_2D", "en", "ltr", 5),
    ],
)
def test_runtime_generated_journeys_map_to_the_exact_registered_scene(
    subject: str,
    block_type: str,
    locale: str,
    direction: str,
    element_count: int,
) -> None:
    scene = AgenticCanvasSceneV1.model_validate(
        _scene(subject=subject, block_type=block_type, element_count=element_count)
    )

    contract = agentic_scene_contract(scene, _brief(subject=subject, locale=locale, direction=direction))

    assert contract["subject_key"] == "CANVAS"
    assert contract["subject_profile_version"] == "agentic-canvas-profile-v1"
    assert contract["activity_key"] == "agentic_canvas"
    assert contract["renderer_key"] == "agentic-canvas"
    assert contract["locale"] == locale
    assert contract["direction"] == direction
    assert contract["seed_payload"] == scene.model_dump(mode="json")
    assert contract["concept_keys"] == (f"agentic:{block_type.lower()}:generated-block",)


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="A disposable PostgreSQL DATABASE_URL is required for settlement acceptance",
)
def test_completed_proposal_settles_to_active_scene_replays_and_reaches_same_tutor(factory) -> None:  # noqa: F811
    """The real PostgreSQL fixture is injected only by explicit disposable-DB runs."""
    with factory.begin() as session:
        user = m.User(identity_provider="agentic-acceptance", external_subject=uuid4().hex)
        session.add(user)
        session.flush()
        student = m.Student(user_id=user.id, display_name="Learner")
        session.add(student)
        session.flush()
        learning = m.LearningSession(student_id=student.id, subject="MATH", status="OPEN")
        session.add(learning)
        session.flush()
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning.id)
        brief = _brief(subject="MATH")
        digest = sha256(json.dumps(brief, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        parent = m.AIExecution(
            task="tutor", provider="fixture", model="fixture", latency_ms=1, success=True,
            student_id=student.id, learning_session_id=learning.id,
        )
        session.add(parent)
        session.flush()
        message = m.LearningMessage(
            session_id=learning.id, role="tutor", content="Let us use the Canvas.", ai_execution_id=parent.id,
            payload={"agentic_canvas": {"status": "ADMITTED", "brief": brief, "brief_digest": digest}},
            created_at=datetime.now(UTC),
        )
        session.add(message)
        session.flush()
        run = admit_agentic_canvas_brief(
            session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id
        )
        assert run is not None
        proposal = _scene(subject="MATH", block_type="MATH_BOARD")
        run.status = "COMPLETED"
        run.proposal_payload = proposal
        run.proposal_digest = sha256(json.dumps(proposal, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        run.completed_at = datetime.now(UTC)
        run_id, runtime_id, student_id, learning_id = run.id, runtime.id, student.id, learning.id

    with factory.begin() as session:
        scene = accept_completed_canvas_run(session, run_id)
        assert scene is not None and scene.status == "ACTIVE"
        assert scene.subject_key == "CANVAS"
        action = {
            "version": "agentic-canvas-action-v1", "action": "SELECT",
            "block_id": "generated-block", "element_id": "element-0",
            "from_value": None, "to_value": None,
        }
        result = StudioStateService(session).append_event(AppendStudioEventCommand(
            runtime_id=runtime_id, student_id=student_id, learning_session_id=learning_id,
            event_kind=None, event_schema_version=None, actor=StudioActor.STUDENT,
            payload_schema_version="agentic-canvas-action-v1", payload=action,
            idempotency_key="acceptance-select", action_key="SELECT",
            scene_id=scene.id, base_scene_version=scene.scene_version,
            subject_key="CANVAS", activity_key="agentic_canvas",
        ))
        assert result.interaction is not None
        replay = StudioStateService(session).rebuild_snapshot(runtime_id=runtime_id, student_id=student_id)
        assert replay == StudioStateService(session).snapshot_projection(result.snapshot)

    selection = select_studio_tutor_context(
        bind=factory.kw["bind"], student_id=student_id, learning_session_id=learning_id,
    )
    assert selection is not None
    model_payload = selection.context.as_model_payload()
    assert model_payload["snapshot"]["visual_scene"]["version"] == "agentic-canvas-tutor-projection-v1"
    assert model_payload["snapshot"]["visual_scene"]["recent_student_actions"][0]["action"] == "SELECT"
    assert model_payload["snapshot"]["current_scene_capability"]["subject_key"] == "CANVAS"
