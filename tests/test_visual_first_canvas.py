"""Visual-first controls and single-choice attempt semantics."""

from __future__ import annotations

from types import SimpleNamespace
import json
from uuid import UUID

import pytest

from services.studio.agent.tools import create_custom_visual
from services.studio.agentic_canvas import AgenticCanvasSceneV1, build_agentic_tutor_projection
from services.studio.full_power_canvas import CanvasSemanticManifestV1
from services.studio.subjects.agentic_canvas import reduce_agentic_canvas, validate_action


def _manifest():
    return CanvasSemanticManifestV1.model_validate({
        "version": "canvas-semantic-manifest-v1", "brief_digest": "a" * 64,
        "objective": "Represent seven plus five accurately.",
        "representation_summary": "Seven blue and five amber counters form twelve counters.",
        "demonstrates": "7 + 5 = 12 by counting all counters.",
        "interpretation_limits": "Counter color identifies each addend; it does not change the total.",
        "suggested_follow_up": "Ask whether regrouping the same counters changes the total.",
        "entities": [
            {"semantic_id": "labels", "kind": "control", "label": "Labels", "educational_meaning": "Show counter group labels.", "visible_description": "Labels toggle."},
            {"semantic_id": "sum-question", "kind": "question", "label": "Total", "educational_meaning": "Choose the total.", "visible_description": "Single-choice question."},
        ],
        "interactions": [
            {"semantic_id": "labels", "action": "TOGGLE", "meaning": "Show or hide group labels.", "value_required": True, "purpose": "LOCAL"},
            {"semantic_id": "sum-question", "action": "SUBMIT", "meaning": "Submit the selected total.", "value_required": True, "purpose": "ANSWER"},
        ],
        "current_state_schema": {"labels": "whether group labels are visible"},
        "choice_questions": [{"semantic_id": "sum-question", "prompt": "What is 7 + 5?", "options": [
            {"value": "12", "label": "12"}, {"value": "13", "label": "13"}, {"value": "17", "label": "17"},
        ]}],
    })


def _scene():
    block = create_custom_visual(
        block_id="addition", meaning="Show 7 + 5 with counters.", label="Counters",
        artifact_instance_id="addition-instance", bridge_nonce="nonce-12345678",
        source="window.mount=(root,params,bridge)=>{root.textContent='7 + 5';}",
        dependencies=["native-svg-v1"], manifest=_manifest(), parameter_schema={},
    )
    return AgenticCanvasSceneV1(version="agentic-canvas-scene-v1", objective="Add the counters.",
        subject_key="MATH", blocks=[block])


def _action(action, *, from_value=None, to_value=None, element_id="sum-question"):
    return {"version": "agentic-canvas-action-v1", "action": action, "block_id": "addition",
        "element_id": element_id, "from_value": from_value, "to_value": to_value}


def _reduce(state, payload, sequence):
    event = SimpleNamespace(sequence=sequence, id=f"event-{sequence}", actor="STUDENT", payload=payload)
    return reduce_agentic_canvas(state, event)


def test_choice_accepts_one_answer_then_requires_explicit_new_attempt():
    scene = _scene().model_dump(mode="json")
    state = {"latest_event_sequence": 0, "last_meaningful_student_event_id": None,
        "state_payload": {"scene_seed": scene, "agentic_canvas": scene}}
    with pytest.raises(ValueError, match="displayed option"):
        validate_action({"action": _action("SUBMIT", to_value="99"), "activity_state": state["state_payload"]})
    wrong = _action("SUBMIT", to_value="17")
    state = _reduce(state, wrong, 1)
    assert next(item for item in state["state_payload"]["agentic_canvas"]["blocks"][0]["elements"] if item["id"] == "sum-question")["current_value"] == "17"
    with pytest.raises(ValueError, match="already has an accepted answer"):
        validate_action({"action": _action("SUBMIT", from_value="17", to_value="12"), "activity_state": state["state_payload"]})
    state = _reduce(state, _action("OPEN_ATTEMPT", from_value="17"), 2)
    assert next(item for item in state["state_payload"]["agentic_canvas"]["blocks"][0]["elements"] if item["id"] == "sum-question")["current_value"] is None
    state = _reduce(state, _action("SUBMIT", to_value="12"), 3)
    assert next(item for item in state["state_payload"]["agentic_canvas"]["blocks"][0]["elements"] if item["id"] == "sum-question")["current_value"] == "12"


def test_local_controls_cannot_create_studio_events_and_projection_is_concise():
    scene = _scene().model_dump(mode="json")
    with pytest.raises(ValueError, match="Local Canvas controls"):
        validate_action({"action": _action("TOGGLE", element_id="labels", to_value="true"),
            "activity_state": {"scene_seed": scene, "agentic_canvas": scene}})
    projection = build_agentic_tutor_projection(objective="Add the counters.", subject_key="MATH",
        scene_status="ACTIVE", blocks=scene["blocks"], actions=[])
    description = projection["blocks"][0]["visual_description"]
    assert description["demonstrates"] == "7 + 5 = 12 by counting all counters."
    assert description["suggested_follow_up"] == "Ask whether regrouping the same counters changes the total."
    assert description["questions"][0]["options"][-1] == {"value": "17", "label": "17"}
    assert "semantic_manifest" not in projection["blocks"][0]


def test_legacy_manifest_serialization_has_no_new_default_keys():
    legacy = CanvasSemanticManifestV1.model_validate({
        "version": "canvas-semantic-manifest-v1", "brief_digest": "b" * 64,
        "objective": "Observe.", "representation_summary": "A simple model.",
        "interactions": [{"semantic_id": "play", "action": "TOGGLE", "meaning": "Play", "value_required": True}],
        "entities": [{"semantic_id": "play", "kind": "control", "label": "Play",
            "educational_meaning": "Starts motion.", "visible_description": "A button."}],
    })
    serialized = legacy.model_dump(mode="json")
    assert "choice_questions" not in serialized
    assert "purpose" not in serialized["interactions"][0]


def test_new_manifest_requires_state_for_local_values_and_app_owned_answer_question():
    valid = _manifest().model_dump(mode="json")
    missing_state = {**valid, "current_state_schema": {}}
    with pytest.raises(ValueError, match="current-state fields"):
        CanvasSemanticManifestV1.model_validate(missing_state)
    missing_question = {**valid, "choice_questions": None}
    with pytest.raises(ValueError, match="application-owned choice question"):
        CanvasSemanticManifestV1.model_validate(missing_question)


def test_live_proof_cap_counts_tutor_and_all_canvas_requests():
    from scripts.prove_visual_first_live import (
        LiveCallBudgetExceeded, MAX_HOSTED_IMAGE_CALLS, MAX_HOSTED_CODE_CALLS,
        ensure_hosted_tool_budget, ensure_request_budget,
    )

    ensure_request_budget(7, 8)
    with pytest.raises(LiveCallBudgetExceeded):
        ensure_request_budget(8, 8)
    ensure_hosted_tool_budget(image_started=MAX_HOSTED_IMAGE_CALLS, code_started=MAX_HOSTED_CODE_CALLS,
        image_tool_available=False, code_tool_available=False)  # Reviewer/finalizer can finish.
    with pytest.raises(LiveCallBudgetExceeded, match="HOSTED_IMAGE_CALL_CAP"):
        ensure_hosted_tool_budget(image_started=MAX_HOSTED_IMAGE_CALLS, code_started=0,
            image_tool_available=True, code_tool_available=False)
    with pytest.raises(LiveCallBudgetExceeded, match="HOSTED_CODE_CALL_CAP"):
        ensure_hosted_tool_budget(image_started=0, code_started=MAX_HOSTED_CODE_CALLS,
            image_tool_available=False, code_tool_available=True)


def test_varied_run_has_frozen_briefs_and_one_consolidated_local_budget(tmp_path):
    from scripts.prove_visual_first_live import (
        ConsolidatedEvaluationBudget, LiveCallBudgetExceeded, REQUESTS,
        LOCAL_CANVAS_EVALUATION_MODEL, frozen_runtime_config, local_evaluation_settings,
    )

    assert tuple(REQUESTS) == ("atom", "addition", "water-cycle", "solar-model", "plant-illustration")
    assert all("12" in REQUESTS["addition"] and option in REQUESTS["addition"] for option in ("13", "17"))
    assert "ماديًا" in REQUESTS["solar-model"] and "صورة" not in REQUESTS["solar-model"]
    assert "رسمة تعليمية أصلية" in REQUESTS["plant-illustration"]
    settings = local_evaluation_settings(root_env=tmp_path / "absent.env",
        database_url="postgresql+psycopg://local@127.0.0.1/lina_learning_test", output=tmp_path)
    assert settings.canvas_model_name == LOCAL_CANVAS_EVALUATION_MODEL == "gpt-6-luna"
    frozen = frozen_runtime_config(settings)
    assert frozen["learner_requests"] == REQUESTS
    assert frozen["canvas_reviewer_model"] == "gpt-6-luna"
    assert frozen["image_tool_available_for"] == list(REQUESTS)
    assert frozen["code_interpreter_max_calls"] == 10
    assert len(frozen["runtime_skill_sha256"]["visual-composition.md"]) == 64
    assert "api_key" not in json.dumps(frozen).lower()
    ledger = ConsolidatedEvaluationBudget(tmp_path / "budget.json", request_limit=5, cost_limit_usd=0.10)
    first = ledger.reserve(case="atom", role="primary_tutor")
    ledger.settle(first, model="gpt-6-luna", input_tokens=100_000, output_tokens=1_000_000)
    with pytest.raises(LiveCallBudgetExceeded, match="COST_CAP"):
        ledger.reserve(case="atom", role="canvas_author")
    reopened = ConsolidatedEvaluationBudget(tmp_path / "budget.json", request_limit=5, cost_limit_usd=0.10)
    assert len(reopened.data["entries"]) == 1


def test_image_allowance_does_not_block_independent_review(tmp_path):
    from scripts.prove_visual_first_live import (
        ConsolidatedEvaluationBudget, IMAGE_COST_RESERVE_USD, CODE_COST_RESERVE_USD,
    )

    ledger = ConsolidatedEvaluationBudget(tmp_path / "budget.json", request_limit=5, cost_limit_usd=1.0)
    author = ledger.reserve(case="plant-illustration", role="canvas_author")
    ledger.settle(author, model="gpt-6-luna", input_tokens=1000, output_tokens=1000,
        hosted_image_calls=1, hosted_code_calls=1)
    assert ledger.data["entries"][author]["image_cost_reserve_usd"] == IMAGE_COST_RESERVE_USD
    assert ledger.data["entries"][author]["code_cost_reserve_usd"] == CODE_COST_RESERVE_USD
    reviewer = ledger.reserve(case="plant-illustration", role="canvas_reviewer")
    ledger.settle(reviewer, model="gpt-6-luna", input_tokens=1000, output_tokens=1000)
    assert all(entry["status"] == "SETTLED" for entry in ledger.data["entries"])


def test_luna_6_outbound_canvas_payload_loads_actual_runtime_guidance():
    from agents import ImageGenerationTool
    from services.studio.agent.intelligence import selected_skill_names
    from services.studio.agent.orchestrator import build_canvas_agent
    from services.studio.canvas_brief import CanvasBriefV1, VisualLearnerContextV1

    brief = CanvasBriefV1.model_validate({"version": "canvas-brief-v1", "subject_key": "SCIENCE",
        "objective": "أرني نبتة صغيرة.", "student_request": "أريد رسمة تعليمية أصلية لنبتة صغيرة.",
        "requested_representation": "رسمة تعليمية", "facts": ["Roots are below soil; stem and leaves are above."],
        "relations": [], "quantities": [], "desired_student_action": None, "must_not_imply": [],
        "source_references": [], "locale": "ar", "direction": "rtl"})
    context = VisualLearnerContextV1.model_validate({"version": "visual-learner-context-v1",
        "core_profile": {"age_years": 10, "grade_level": "5"}, "selected_personal_facts": []})
    assert "image-composition.md" in selected_skill_names(brief, context)
    agent = build_canvas_agent(api_key="test-only-key", model="gpt-6-luna", brief=brief,
        visual_learner_context=context, image_generation_model="gpt-image-2.5-flare",
        reasoning_effort="medium", sdk_max_retries=0)
    image_tool = next(tool for tool in agent.tools if isinstance(tool, ImageGenerationTool))
    assert image_tool.tool_config["model"] == "gpt-image-2.5-flare"
    outbound = agent.model._build_response_create_kwargs(system_instructions=agent.instructions,
        input="test", model_settings=agent.model_settings, tools=agent.tools, output_schema=None, handoffs=[], stream=False)
    assert outbound["model"] == "gpt-6-luna"
    assert outbound["reasoning"].effort == "medium"
    assert any(tool.get("type") == "image_generation" and tool.get("model") == "gpt-image-2.5-flare"
        for tool in outbound["tools"])
    assert "Teach through the representation itself" in outbound["instructions"]
    assert "An image may lead the Scene" in outbound["instructions"]
    assert "Choose by the needed visual meaning, not the subject name" in outbound["instructions"]
    reviewer = agent.clone(name="Lina Canvas verification", model=agent.model,
        model_settings=agent.model_settings, tools=[])
    review_request = reviewer.model._build_response_create_kwargs(system_instructions=reviewer.instructions,
        input="test", model_settings=reviewer.model_settings, tools=[], output_schema=None, handoffs=[], stream=False)
    assert review_request["model"] == "gpt-6-luna"
    assert review_request["reasoning"].effort == "medium"


@pytest.mark.parametrize("case,subject,expected_specialist", [
    ("atom", "SCIENCE", "diagrams-and-processes.md"),
    ("addition", "MATH", "math-visualization.md"),
    ("water-cycle", "SCIENCE", "diagrams-and-processes.md"),
    ("solar-model", "SCIENCE", "diagrams-and-processes.md"),
    ("plant-illustration", "SCIENCE", "image-composition.md"),
])
def test_frozen_case_guidance_loads_in_application(case, subject, expected_specialist):
    from scripts.prove_visual_first_live import REQUESTS
    from services.studio.agent.intelligence import selected_skill_names
    from services.studio.canvas_brief import CanvasBriefV1, VisualLearnerContextV1
    from services.studio.agent.orchestrator import build_canvas_agent

    brief = CanvasBriefV1.model_validate({"version": "canvas-brief-v1", "subject_key": subject,
        "objective": REQUESTS[case], "student_request": REQUESTS[case],
        "requested_representation": None, "facts": [], "relations": [], "quantities": [],
        "desired_student_action": None, "must_not_imply": [], "source_references": [],
        "locale": "ar", "direction": "rtl"})
    context = VisualLearnerContextV1.model_validate({"version": "visual-learner-context-v1",
        "core_profile": {"age_years": 10, "grade_level": "5"}, "selected_personal_facts": []})
    selected = selected_skill_names(brief, context)
    assert "visual-composition.md" in selected and expected_specialist in selected
    agent = build_canvas_agent(api_key="test-only-key", model="gpt-6-luna", brief=brief,
        visual_learner_context=context, image_generation_allowed=True)
    assert "Teach through the representation itself" in agent.instructions
    assert "A local control changes the sandbox immediately" in agent.instructions
    assert "The application renders and locks those options" in agent.instructions
    assert "The Primary Tutor" in agent.instructions


def test_local_evaluation_reasoning_retry_and_candidate_limits_are_explicit():
    from scripts.prove_visual_first_live import (
        CandidateRepairLimitExceeded, ensure_candidate_repair_allowed,
    )
    from services.studio.agent.orchestrator import build_canvas_agent

    shared = build_canvas_agent(api_key="test-only-key", model="gpt-5.6-luna")
    local = build_canvas_agent(api_key="test-only-key", model="gpt-6-luna",
        reasoning_effort="medium", sdk_max_retries=0)
    assert shared.model_settings.reasoning is None
    assert shared.model._client.max_retries == 2
    assert local.model_settings.reasoning.effort == "medium"
    assert local.model._client.max_retries == 0
    ensure_candidate_repair_allowed(attempt=1, defect_recorded=False)
    ensure_candidate_repair_allowed(attempt=2, defect_recorded=True)
    with pytest.raises(CandidateRepairLimitExceeded, match="REPAIR_REQUIRES_CONCRETE_DEFECT"):
        ensure_candidate_repair_allowed(attempt=2, defect_recorded=False)
    with pytest.raises(CandidateRepairLimitExceeded, match="THIRD_CANDIDATE_FORBIDDEN"):
        ensure_candidate_repair_allowed(attempt=3, defect_recorded=True)


def _atom_workspace(*, state_version=2):
    from services.studio.tutor_context import StudioTutorSceneCapability, StudioTutorWorkspaceContext

    scene_id = UUID("33333333-3333-4333-8333-333333333333")
    manifest = CanvasSemanticManifestV1.model_validate({
        "version": "canvas-semantic-manifest-v1", "brief_digest": "c" * 64,
        "objective": "Explain one atom moving about equilibrium.",
        "representation_summary": "One atom moves back and forth about a fixed equilibrium position.",
        "demonstrates": "Displacement changes while equilibrium remains fixed.",
        "interpretation_limits": "Illustrative motion, not an electron orbit or a scale model.",
        "entities": [{"semantic_id": control, "kind": "control", "label": control,
            "educational_meaning": control, "visible_description": control}
            for control in ("playing", "speed", "show_labels")],
        "interactions": [
            {"semantic_id": "playing", "action": "TOGGLE", "meaning": "Pause or play motion.", "value_required": True, "purpose": "LOCAL"},
            {"semantic_id": "speed", "action": "SET_VALUE", "meaning": "Change display speed only.", "value_required": True, "purpose": "LOCAL"},
            {"semantic_id": "show_labels", "action": "TOGGLE", "meaning": "Show or hide labels.", "value_required": True, "purpose": "LOCAL"},
        ],
        "current_state_schema": {"playing": "play state", "speed": "display speed", "show_labels": "label visibility"},
    })
    block = create_custom_visual(block_id="atom", meaning=manifest.representation_summary, label="Atom",
        artifact_instance_id="atom-test", bridge_nonce="atom-test-nonce",
        source="window.mount=(root,params,bridge)=>{root.textContent='atom';}",
        dependencies=["native-svg-v1"], manifest=manifest, parameter_schema={})
    visual = build_agentic_tutor_projection(objective=manifest.objective, subject_key="SCIENCE",
        scene_status="ACTIVE", blocks=[block.model_dump(mode="json")], actions=[])
    return StudioTutorWorkspaceContext(
        runtime_id=UUID("22222222-2222-4222-8222-222222222222"),
        snapshot_schema_version="studio-snapshot-v1", through_sequence=3, snapshot_sequence=3,
        current_scene_id=scene_id, current_scene_version=2, active_subject_key="CANVAS",
        active_activity_key="agentic_canvas", state_payload={"scene_status": "ACTIVE"},
        unseen_events=(), observation_id=None, visual_scene=visual,
        current_scene_capability=StudioTutorSceneCapability(scene_id=scene_id, subject_key="SCIENCE",
            subject_profile_version="agentic-canvas-profile-v3", activity_key="agentic_canvas",
            activity_version="agentic-canvas-activity-v1", renderer_key="agentic-canvas",
            renderer_version="agentic-canvas-renderer-v3", allowed_action_keys=("TOGGLE", "SET_VALUE"),
            source_references=()),
        canvas_composition={"run_id": "run-atom", "run_status": "COMPLETED", "scene_ready": True,
            "scene_id": str(scene_id), "active_scene_id": str(scene_id), "active_scene_version": 2,
            "objective": manifest.objective, "source_message_id": "source-atom"},
        local_visual_state={"scene_id": str(scene_id), "scene_version": state_version,
            "block_id": "atom", "values": {"playing": "false", "speed": "2", "show_labels": "false"},
            "authority": "Browser-reported exploration only; not grading, authorization, or Learning Evidence."},
    )


def test_atom_full_tutor_request_has_one_bounded_current_visual_and_no_duplicate_contracts():
    from services.tutor.runtime import build_tutor_model_payload

    context = _atom_workspace()
    for question in ("Why does the atom return near equilibrium?", "What is Japan's capital?"):
        request = build_tutor_model_payload(question=question, studio_context=context)
        snapshot = context.as_model_payload()["snapshot"]
        card = snapshot["current_visual"]
        assert "visual_scene" not in snapshot and "local_visual_state" not in snapshot
        assert card["what_is_shown"] == "One atom moves back and forth about a fixed equilibrium position."
        assert {item["id"]: item["current_value"] for item in card["controls"]} == {
            "playing": "false", "speed": "2", "show_labels": "false"}
        assert len(json.dumps(card, ensure_ascii=False, separators=(",", ":")).encode()) <= 4096
        assert request["input"].count(card["what_is_shown"]) == 1
        assert '"instance_parameters"' not in request["input"]
        assert '"source_manifest_digest"' not in request["input"]
        assert request["input"].count('"run_id": "run-atom"') == 1


def test_atom_replacement_discards_old_browser_values_from_current_card():
    card = _atom_workspace(state_version=1).as_model_payload()["snapshot"]["current_visual"]
    assert all("current_value" not in item for item in card["controls"])




def test_canvas_interaction_visual_change_uses_application_owned_request_and_sources():
    from services.studio.interactions import (
        StudioInteractionTutorContext,
        _bind_canvas_interaction_brief,
    )
    from services.studio.tutor_context import StudioTutorSceneCapability, StudioTutorWorkspaceContext

    context = StudioInteractionTutorContext(
        interaction_id=UUID("77777777-7777-4777-8777-777777777777"),
        runtime_id=UUID("22222222-2222-4222-8222-222222222222"),
        learning_session_id=UUID("11111111-1111-4111-8111-111111111111"),
        source={
            "current_interaction": {
                "action": "REQUEST_EXPLANATION",
                "target_id": "stage-2",
                "target_kind": "object",
                "label": "Stage 2",
                "detail": "The learner asked for this stage to be explained.",
            },
            "event": {"sequence": 4, "action_key": "EXPLAIN"},
        },
        workspace={"current_scene_id": "33333333-3333-4333-8333-333333333333", "state": {}},
    )
    workspace = StudioTutorWorkspaceContext(
        runtime_id=context.runtime_id,
        snapshot_schema_version="studio-snapshot-v1",
        through_sequence=4,
        snapshot_sequence=4,
        current_scene_id=UUID("33333333-3333-4333-8333-333333333333"),
        current_scene_version=2,
        active_subject_key="SCIENCE",
        active_activity_key="agentic_canvas",
        state_payload={},
        unseen_events=(),
        observation_id=None,
        current_scene_capability=StudioTutorSceneCapability(
            scene_id=UUID("33333333-3333-4333-8333-333333333333"),
            subject_key="SCIENCE",
            subject_profile_version="v1",
            activity_key="agentic_canvas",
            activity_version="v1",
            renderer_key="agentic_canvas",
            renderer_version="v1",
            allowed_action_keys=("EXPLAIN",),
            source_references=("book#page=8",),
        ),
    )
    model_brief = {
        "version": "canvas-brief-v1",
        "subject_key": "SCIENCE",
        "objective": "Clarify the stage.",
        "relevant_conversation": None,
        "facts": ["The stage follows the prior stage."],
        "relations": [],
        "quantities": [],
        "desired_student_action": "Inspect the changed explanation.",
        "source_references": ["model-invented-id"],
        "locale": "en",
        "direction": "ltr",
    }

    bound = _bind_canvas_interaction_brief(
        model_brief,
        context=context,
        workspace_context=workspace,
    )

    assert bound["source_references"] == ["book#page=8"]
    assert bound["student_request"].startswith("Canvas interaction:")
    assert "REQUEST_EXPLANATION" in bound["student_request"]
    assert "model-invented-id" not in str(bound)

def test_existing_answer_request_keeps_exact_source_once_without_snapshot_duplication():
    from services.studio.interactions import StudioInteractionTutorContext, StudioInteractionTutorService
    from services.studio.tutor_context import StudioTutorEventContext, StudioTutorWorkspaceContext

    scene = _scene().model_dump(mode="json")
    scene_id = UUID("33333333-3333-4333-8333-333333333333")
    scene["blocks"][0]["elements"][1]["current_value"] = "17"
    visual = build_agentic_tutor_projection(objective=scene["objective"], subject_key="MATH",
        scene_status="ACTIVE", blocks=scene["blocks"], actions=[])
    action = _action("SUBMIT", to_value="17")
    source = {"current_interaction": {
        "action": "ANSWER_CHOICE", "question_id": "sum-question", "question": "What is 7 + 5?",
        "displayed_options": [{"value": "12", "label": "12"}, {"value": "13", "label": "13"}, {"value": "17", "label": "17"}],
        "learner_answer": {"value": "17", "label": "17"},
        "visual_context": {"what_is_shown": _manifest().representation_summary,
            "demonstrates": _manifest().demonstrates, "interpretation_limits": _manifest().interpretation_limits},
    }, "event": {"sequence": 4, "action_key": "SUBMIT", "scene_id": str(scene_id),
                 "scene_version": 2, "activity_key": "agentic_canvas", "action_payload": action}}
    interaction = StudioInteractionTutorContext(interaction_id=UUID("77777777-7777-4777-8777-777777777777"),
        runtime_id=UUID("22222222-2222-4222-8222-222222222222"), learning_session_id=UUID("11111111-1111-4111-8111-111111111111"),
        source=source, workspace={"current_scene_id": str(scene_id), "current_scene_version": 2,
            "state": {"scene_seed": scene, "agentic_canvas": scene}})
    workspace = StudioTutorWorkspaceContext(runtime_id=interaction.runtime_id, snapshot_schema_version="studio-snapshot-v1",
        through_sequence=4, snapshot_sequence=4, current_scene_id=scene_id, current_scene_version=2,
        active_subject_key="CANVAS", active_activity_key="agentic_canvas", state_payload={"scene_status": "ACTIVE"},
        unseen_events=(StudioTutorEventContext(sequence=4, actor="STUDENT", event_kind="answer",
            action_key="SUBMIT", subject_key="MATH", activity_key="agentic_canvas", base_scene_version=1,
            resulting_scene_version=2, payload_schema_version="agentic-canvas-action-v1", payload={"action": action}),),
        observation_id=None, visual_scene=visual)
    payload = StudioInteractionTutorService(bind=object(), gateway_factory=lambda _: None)._model_payload(
        interaction, workspace_context=workspace)
    assembled = payload["input"]
    assert assembled.count("What is 7 + 5?") == 1
    assert assembled.count('"displayed_options"') == 1
    assert '"action_payload"' not in assembled
    assert '"scene_seed"' not in assembled
    assert '"interaction_id": "77777777-7777-4777-8777-777777777777"' in assembled
    assert payload["studio_workspace_context"]["snapshot"]["current_visual"]["what_is_shown"] == _manifest().representation_summary
    assert "question" not in payload["studio_workspace_context"]["snapshot"]["current_visual"]
