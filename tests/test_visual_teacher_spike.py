"""Provider-free contract probe for the new equivalent-fractions topic."""

from __future__ import annotations

import json
from uuid import UUID

from services.studio.agent.orchestrator import (
    _canonical_custom_manifest, build_canvas_agent, canvas_agent_input,
)
from services.studio.agent.tools import create_custom_visual
from services.studio.agentic_canvas import build_agentic_tutor_projection
from services.studio.canvas_brief import (
    CanvasBriefV1, VisualLearnerContextV1, audit_canvas_brief, bind_tutor_canvas_brief,
)
from services.studio.full_power_canvas import CanvasSemanticEntityV1, CanvasSemanticInteractionV1
from services.studio.tutor_context import StudioTutorWorkspaceContext
from services.tutor.runtime import build_tutor_model_payload


def _run_equivalent_fractions_probe() -> dict[str, object]:
    student_request = "Why are 1/2 and 2/4 equal? Show me visually."
    tutor_brief = {
        "version": "canvas-brief-v1", "subject_key": "MATH",
        "objective": "Show why 1/2 and 2/4 cover the same amount of one whole.",
        "relevant_conversation": "The learner wants to compare equal amounts before discussing the rule.",
        "facts": [
            "Both fractions refer to the same-size whole and equal-size parts.",
            "Repartitioning a half into two equal fourths preserves the represented amount.",
        ],
        "relations": [],
        "quantities": [{"id": "one_half", "value": "1/2", "unit": None},
                       {"id": "two_quarters", "value": "2/4", "unit": None}],
        "desired_student_action": "Explore how repartitioning the same whole preserves the shaded amount.",
        "source_references": [], "locale": "en", "direction": "ltr",
    }
    brief = CanvasBriefV1.model_validate(
        bind_tutor_canvas_brief(tutor_brief, student_request=student_request)
    )
    admitted = audit_canvas_brief(brief.model_dump(mode="json"),
        allowed_source_references=set(), safety_allows=True)
    assert admitted["status"] == "ADMITTED"
    learner = VisualLearnerContextV1.model_validate({"version": "visual-learner-context-v1",
        "core_profile": {"age_years": 10, "grade_level": "5"}, "selected_personal_facts": []})
    agent_input = json.loads(canvas_agent_input(brief, learner))
    assert agent_input["canvas_brief"]["student_request"] == student_request
    assert "requested_representation" not in agent_input["canvas_brief"]
    assert "must_not_imply" not in agent_input["canvas_brief"]
    assert agent_input["canvas_brief"]["relevant_conversation"] == brief.relevant_conversation
    agent = build_canvas_agent(api_key="test-only-key", model="gpt-6-luna",
        brief=brief, visual_learner_context=learner, reasoning_effort="medium", sdk_max_retries=0)
    assert "visual teaching specialist" in agent.instructions
    assert any(tool.name == "create_custom_visual" for tool in agent.tools)

    # Deterministic stand-in for an authored Manifest. This checks the return
    # boundary; it does not claim that a model chose this representation.
    manifest = _canonical_custom_manifest(
        brief_digest=admitted["brief_digest"], objective=brief.objective,
        meaning="Two same-size bars show one of two and two of four equal parts shaded.",
        demonstrates="1/2 and 2/4 cover the same amount when the whole stays fixed.",
        interpretation_limits="Both bars must represent the same-size whole.",
        suggested_follow_up="Ask what changes when each half is split into two equal pieces.",
        entities=[CanvasSemanticEntityV1.model_validate({"semantic_id": "partition", "kind": "control", "label": "Partition",
            "educational_meaning": "Change the number of equal parts while keeping the amount.",
            "visible_description": "Partition control."})],
        interactions=[CanvasSemanticInteractionV1.model_validate({"semantic_id": "partition", "action": "SET_VALUE",
            "meaning": "Repartition the same whole into two or four equal parts.",
            "value_required": True, "purpose": "LOCAL"})],
        relations=[], quantities=[], presentation_steps=[], visual_descriptions=[],
        current_state_schema={"partition": "number of equal parts"},
    )
    block = create_custom_visual(block_id="fraction_probe", meaning=manifest.representation_summary,
        label="Equivalent fractions", artifact_instance_id="fraction-probe",
        bridge_nonce="fraction-probe-nonce",
        source="window.mount=(root,params,bridge)=>{root.textContent='1/2 = 2/4';}",
        dependencies=["native-svg-v1"], manifest=manifest, parameter_schema={})
    projection = build_agentic_tutor_projection(objective=brief.objective, subject_key="MATH",
        scene_status="ACTIVE", blocks=[block.model_dump(mode="json")], actions=[])
    description = projection["blocks"][0]["visual_description"]
    assert description["activity_type"] == "exploration"
    assert description["suggested_follow_up"] == manifest.suggested_follow_up
    context = StudioTutorWorkspaceContext(
        runtime_id=UUID("22222222-2222-4222-8222-222222222222"),
        snapshot_schema_version="studio-snapshot-v1", through_sequence=0, snapshot_sequence=0,
        current_scene_id=UUID("33333333-3333-4333-8333-333333333333"),
        current_scene_version=1, active_subject_key="CANVAS", active_activity_key="agentic_canvas",
        state_payload={"scene_status": "ACTIVE"}, unseen_events=(), observation_id=None,
        visual_scene=projection, local_visual_state={"scene_id": "33333333-3333-4333-8333-333333333333",
            "scene_version": 1, "block_id": "fraction_probe", "values": {"partition": "4"}},
    )
    card = context.as_model_payload()["snapshot"]["current_visual"]
    assert card["controls"] == [{"id": "partition",
        "effect": "Repartition the same whole into two or four equal parts.", "current_value": "4"}]
    assert card["suggested_follow_up"] == manifest.suggested_follow_up
    assembled = build_tutor_model_payload(question="What stayed the same when I used four parts?",
        studio_context=context)["input"]
    assert assembled.count(manifest.representation_summary) == 1
    assert assembled.count(manifest.suggested_follow_up) == 1
    assert '"current_value": "4"' in assembled
    assert '"semantic_manifest"' not in assembled
    assert "window.mount" not in assembled
    return {"brief": admitted["brief"], "canvas_agent_input": agent_input,
        "raw_projection": projection, "visual_teaching_summary": card,
        "prepared_tutor_input": assembled}


def test_equivalent_fractions_handoff_and_same_tutor_semantic_return() -> None:
    _run_equivalent_fractions_probe()
