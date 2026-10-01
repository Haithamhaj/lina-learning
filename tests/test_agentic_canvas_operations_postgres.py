"""Authenticated Agentic Canvas operation admission and durable current-state proof."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4

import pytest

from test_studio_make_ten_postgres import (
    _activate,
    _clear_overrides,
    _client,
    _learning_session,
    _student,
    postgres_session_factory,  # noqa: F401 - imported pytest fixture
)
from services.studio.contracts import CreateSceneCommand
from services.studio.service import StudioStateService
from services.studio.tutor_context import select_studio_tutor_context
from services.studio.custom_visual_builds import CustomVisualBuildResolver
from services.platform.db.models import StudioEvent, StudioRuntime, StudioStudentInteraction
from services.studio.interactions import StudioInteractionTutorService
from uuid import UUID
from sqlalchemy import select


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Disposable PostgreSQL DATABASE_URL is required for Agentic Canvas operations",
)


def _scene() -> dict[str, object]:
    return {
        "version": "agentic-canvas-scene-v2",
        "objective": "Compare the quantities.",
        "subject_key": "MATH",
        "presentation": {"layout": "FOCUS", "palette": "COOL", "motion": "NONE", "placements": [{"block_id": "number-line", "role": "PRIMARY", "order": 0, "span": "FULL"}], "reveal_order": []},
        "blocks": [{
            "block_id": "number-line", "type": "MATH_BOARD",
            "meaning": "Compare exact positions.", "title": "Number line",
            "accessibility": {"text_equivalent": "An exact number line.", "aria_label": None},
            "allowed_actions": ["SET_VALUE"],
            "elements": [{"id": "point-a", "label": "Point A", "current_value": "3/5"}],
            "board_kind": "NUMBER_LINE", "axis_min": "0", "axis_max": "1",
        }],
    }


def test_authenticated_agentic_operation_accepts_known_semantics_and_rejects_unknown_element(
    postgres_session_factory,  # noqa: F811 - pytest injects the imported fixture
) -> None:
    with postgres_session_factory.begin() as session:
        student = _student(session, "agentic-operation")
        learning = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning.id)
        scene = service.accept_scene(CreateSceneCommand(
            student_id=student.id, learning_session_id=learning.id,
            subject_key="CANVAS", subject_profile_version="agentic-canvas-profile-v2",
            concept_keys=("fraction-comparison",), activity_key="agentic_canvas",
            artifact_type="agentic-canvas", renderer_key="agentic-canvas",
            renderer_version="agentic-canvas-renderer-v2",
            activity_contract_version="agentic-canvas-activity-v1",
            payload_schema_version="agentic-canvas-scene-v2", seed_payload=_scene(),
            accessibility_payload={"text_equivalent": "An exact number line."},
            locale="en", direction="ltr",
        ))
        _activate(service, runtime_id=runtime.id, student=student, learning_session=learning, scene=scene)
        runtime_id, scene_id, scene_version = runtime.id, scene.id, scene.scene_version

    client = _client(postgres_session_factory, subject="agentic-operation")
    try:
        def operation(element_id: str, nonce: str):
            return client.post(
                f"/api/v1/student/studio/{runtime_id}/operations",
                json={
                    "scene_id": str(scene_id), "base_scene_version": scene_version,
                    "action_key": "SET_VALUE", "idempotency_key": nonce,
                    "payload": {
                        "version": "agentic-canvas-action-v1", "action": "SET_VALUE",
                        "block_id": "number-line", "element_id": element_id,
                        "from_value": "3/5", "to_value": "4/5",
                    },
                },
            )

        rejected = operation("unknown", "agentic-unknown")
        assert rejected.status_code == 422
        accepted = operation("point-a", "agentic-set-value")
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["student_interaction_status"] == "PENDING"
        snapshot = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot").json()
        assert snapshot["state_payload"]["agentic_canvas"]["blocks"][0]["elements"][0]["current_value"] == "4/5"
    finally:
        _clear_overrides()


def test_classification_move_reaches_tutor_as_learner_state_without_losing_solution_semantics(
    postgres_session_factory,  # noqa: F811
) -> None:
    scene_seed = {
        "version": "agentic-canvas-scene-v2", "objective": "Classify the slopes.", "subject_key": "MATH",
        "presentation": {"layout": "STACK", "palette": "COOL", "motion": "NONE", "placements": [{"block_id": "classify", "role": "INTERACTION", "order": 0, "span": "FULL"}], "reveal_order": []},
        "blocks": [{
            "block_id": "classify", "type": "TEXT_INTERACTION", "meaning": "Classify each line by slope.",
            "title": "Slope groups", "accessibility": {"text_equivalent": "Two slope categories.", "aria_label": None},
            "allowed_actions": ["MOVE"],
            "elements": [
                {"id": "steep", "label": "Steep line", "current_value": None},
                {"id": "gentle", "label": "Gentle line", "current_value": None},
                {"id": "fastest", "label": "Fastest", "current_value": None},
                {"id": "not-fastest", "label": "Not fastest", "current_value": None},
            ],
            "interaction_family": "CLASSIFICATION", "prompt": "Place one line.",
            "items": [
                {"id": "steep", "text": "Steep line", "group_id": "fastest"},
                {"id": "gentle", "text": "Gentle line", "group_id": "not-fastest"},
            ],
            "groups": [{"id": "fastest", "label": "Fastest"}, {"id": "not-fastest", "label": "Not fastest"}],
            "relations": [],
        }],
    }
    with postgres_session_factory.begin() as session:
        student = _student(session, "agentic-classification-state")
        learning = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning.id)
        scene = service.accept_scene(CreateSceneCommand(
            student_id=student.id, learning_session_id=learning.id, subject_key="CANVAS",
            subject_profile_version="agentic-canvas-profile-v2", concept_keys=("linear-slope",),
            activity_key="agentic_canvas", artifact_type="agentic-canvas", renderer_key="agentic-canvas",
            renderer_version="agentic-canvas-renderer-v2", activity_contract_version="agentic-canvas-activity-v1",
            payload_schema_version="agentic-canvas-scene-v2", seed_payload=scene_seed,
            accessibility_payload={"text_equivalent": "Classify two lines."}, locale="en", direction="ltr",
        ))
        _activate(service, runtime_id=runtime.id, student=student, learning_session=learning, scene=scene)
        runtime_id, scene_id, scene_version = runtime.id, scene.id, scene.scene_version
        student_id, learning_id = student.id, learning.id

    client = _client(postgres_session_factory, subject="agentic-classification-state")
    try:
        response = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id), "base_scene_version": scene_version,
                "action_key": "MOVE", "idempotency_key": "classify-steep",
                "payload": {"version": "agentic-canvas-action-v1", "action": "MOVE", "block_id": "classify", "element_id": "steep", "from_value": None, "to_value": "fastest"},
            },
        )
        assert response.status_code == 200, response.text
    finally:
        _clear_overrides()

    selection = select_studio_tutor_context(
        bind=postgres_session_factory.kw["bind"], student_id=student_id, learning_session_id=learning_id,
    )
    assert selection is not None
    visual = selection.context.as_model_payload()["snapshot"]["visual_scene"]
    block = visual["blocks"][0]
    assert next(item for item in block["elements"] if item["id"] == "steep")["current_value"] == "fastest"
    assert block["solution_semantics"]["item_group_assignments"][0] == {"item_id": "steep", "group_id": "fastest"}
    assert visual["recent_student_actions"][-1]["to"] == "fastest"


def test_visual_first_choice_has_one_durable_answer_per_attempt_under_competing_requests(
    postgres_session_factory, monkeypatch,  # noqa: F811
) -> None:
    from test_visual_first_canvas import _scene

    authored = _scene()
    package = authored.blocks[0].package
    assert package is not None
    digest = "d" * 64
    monkeypatch.setattr(CustomVisualBuildResolver, "resolve", lambda self, session, **kwargs:
        SimpleNamespace(package=package, manifest_digest=digest))
    block = authored.blocks[0].model_dump(mode="json")
    block.update(package=None, custom_visual_build_id=str(uuid4()), manifest_digest=digest)
    seed = {"version": "agentic-canvas-scene-v3", "objective": "Add the counters.", "subject_key": "MATH",
        "presentation": {"layout": "FOCUS", "palette": "COOL", "motion": "NONE",
            "placements": [{"block_id": "addition", "role": "PRIMARY", "order": 0, "span": "FULL"}], "reveal_order": []},
        "blocks": [block]}
    with postgres_session_factory.begin() as session:
        student = _student(session, "visual-first-choice")
        learning = _learning_session(session, student)
        service = StudioStateService(session)
        runtime = service.get_or_create_runtime(student_id=student.id, learning_session_id=learning.id)
        scene = service.accept_scene(CreateSceneCommand(
            student_id=student.id, learning_session_id=learning.id, subject_key="CANVAS",
            subject_profile_version="agentic-canvas-profile-v3", concept_keys=("addition",),
            activity_key="agentic_canvas", artifact_type="agentic-canvas", renderer_key="agentic-canvas",
            renderer_version="agentic-canvas-renderer-v3", activity_contract_version="agentic-canvas-activity-v1",
            payload_schema_version="agentic-canvas-scene-v3", seed_payload=seed,
            accessibility_payload={"text_equivalent": "Seven plus five counters."}, locale="en", direction="ltr",
        ))
        _activate(service, runtime_id=runtime.id, student=student, learning_session=learning, scene=scene)
        runtime_id, scene_id, version = runtime.id, scene.id, scene.scene_version

    client = _client(postgres_session_factory, subject="visual-first-choice")
    path = f"/api/v1/student/studio/{runtime_id}/operations"
    def submit(action, answer, base_version, key, previous=None):
        return client.post(path, json={"scene_id": str(scene_id), "base_scene_version": base_version,
            "action_key": action, "idempotency_key": key,
            "payload": {"version": "agentic-canvas-action-v1", "action": action,
                "block_id": "addition", "element_id": "sum-question", "from_value": previous, "to_value": answer}})
    try:
        local = submit("TOGGLE", "true", version, "local-should-not-save")
        assert local.status_code == 422
        first = submit("SUBMIT", "17", version, "answer-17")
        assert first.status_code == 200, first.text
        assert first.json()["student_interaction_id"] is not None
        with postgres_session_factory() as session:
            interaction = session.get(StudioStudentInteraction, UUID(first.json()["student_interaction_id"]))
            runtime_row = session.get(StudioRuntime, runtime_id)
            source = StudioInteractionTutorService(bind=postgres_session_factory.kw["bind"],
                gateway_factory=lambda _: None)._resolve_context(
                admission_session=session, runtime=runtime_row, interaction=interaction).as_model_payload()["source"]
            assert source["current_interaction"] == {
                "action": "ANSWER_CHOICE", "question_id": "sum-question", "question": "What is 7 + 5?",
                "displayed_options": [{"value": "12", "label": "12"}, {"value": "13", "label": "13"}, {"value": "17", "label": "17"}],
                "learner_answer": {"value": "17", "label": "17"},
                "visual_context": {"what_is_shown": "Seven blue and five amber counters form twelve counters.",
                    "demonstrates": "7 + 5 = 12 by counting all counters.",
                    "interpretation_limits": "Counter color identifies each addend; it does not change the total."},
            }
        with ThreadPoolExecutor(max_workers=2) as pool:
            retry = pool.submit(submit, "SUBMIT", "17", version, "answer-17")
            competing = pool.submit(submit, "SUBMIT", "12", version, "answer-12")
            assert retry.result().json()["replayed"] is True
            assert competing.result().status_code == 409
        current = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot").json()
        assert current["state_payload"]["agentic_canvas"]["blocks"][0]["elements"][1]["current_value"] == "17"
        supplied = {"scene_id": str(scene_id), "scene_version": current["current_scene_version"],
            "block_id": "addition", "values": {"labels": "shown"}}
        selection = select_studio_tutor_context(bind=postgres_session_factory.kw["bind"],
            student_id=student.id, learning_session_id=learning.id, local_visual_state=supplied)
        current_card = selection.context.as_model_payload()["snapshot"]["current_visual"]
        assert {item["id"]: item["current_value"] for item in current_card["controls"]} == {"labels": "shown"}
        assert current_card["current_values_authority"] == "browser_advisory"
        stale = select_studio_tutor_context(bind=postgres_session_factory.kw["bind"],
            student_id=student.id, learning_session_id=learning.id,
            local_visual_state={**supplied, "scene_version": version})
        stale_card = stale.context.as_model_payload()["snapshot"]["current_visual"]
        assert all("current_value" not in item for item in stale_card["controls"])
        with postgres_session_factory.begin() as session:
            interaction = session.get(StudioStudentInteraction, first.json()["student_interaction_id"])
            interaction.status = "COMPLETED"
        new_version = current["current_scene_version"]
        opened = submit("OPEN_ATTEMPT", None, new_version, "new-attempt", previous="17")
        assert opened.status_code == 200, opened.text
        assert opened.json()["student_interaction_id"] is None
        reopened = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot").json()
        assert reopened["state_payload"]["agentic_canvas"]["blocks"][0]["elements"][1]["current_value"] is None
        with ThreadPoolExecutor(max_workers=2) as pool:
            left = pool.submit(submit, "SUBMIT", "12", reopened["current_scene_version"], "second-12")
            right = pool.submit(submit, "SUBMIT", "13", reopened["current_scene_version"], "second-13")
            statuses = sorted([left.result().status_code, right.result().status_code])
        assert statuses == [200, 409]
        with postgres_session_factory() as session:
            accepted = session.scalars(select(StudioEvent).where(StudioEvent.studio_runtime_id == runtime_id,
                StudioEvent.action_key == "SUBMIT")).all()
            assert len(accepted) == 2
    finally:
        _clear_overrides()
