from __future__ import annotations


def test_single_canvas_agent_uses_only_the_bounded_tool_registry() -> None:
    from services.studio.agent.orchestrator import build_canvas_agent
    from services.studio.agent.tools import tool_names
    from services.studio.agentic_canvas import AgenticCanvasPlanV1

    agent = build_canvas_agent(api_key="test-only-key", model="gpt-5.6-luna")

    assert agent.handoffs == []
    assert tuple(tool.name for tool in agent.tools) == tool_names()
    assert agent.output_type is AgenticCanvasPlanV1
    assert "Tutor" in agent.instructions
    assert "write Studio" in agent.instructions
    schemas = {
        tool.name: getattr(tool, "params_json_schema", None)
        for tool in agent.tools
    }
    assert set(schemas["create_math_board"]["properties"]) >= {"axes", "markers", "expressions"}
    assert set(schemas["create_2d_scene"]["properties"]) >= {"objects", "relations"}
    assert set(schemas["create_diagram"]["properties"]) >= {"nodes", "edges"}
    assert set(schemas["create_text_interaction"]["properties"]) >= {"items", "groups", "relations"}
    custom_schema = schemas["create_custom_visual"]
    assert {"entities", "interactions", "source"} <= set(custom_schema["properties"])
    assert "manifest" not in custom_schema["properties"]
    assert "artifact_instance_id" not in custom_schema["properties"]
    code_tool = next(tool for tool in agent.tools if tool.name == "code_interpreter")
    assert code_tool.tool_config == {"type": "code_interpreter", "container": {"type": "auto"}}


def test_agentic_canvas_deadline_allows_one_bounded_custom_visual_composition() -> None:
    from datetime import timedelta

    from services.studio.agent.admission import AGENTIC_CANVAS_DEADLINE

    assert AGENTIC_CANVAS_DEADLINE == timedelta(minutes=5)


def test_canvas_agent_instructions_make_hosted_tool_selection_semantic_and_bounded() -> None:
    from services.studio.agent.orchestrator import CANVAS_AGENT_INSTRUCTIONS

    instructions = CANVAS_AGENT_INSTRUCTIONS.casefold()
    assert "original illustrative image" in instructions
    assert "typed geometric or diagram primitives" in instructions
    assert "do not replace that requested illustration with typed primitives" in instructions
    assert "long bounded recurrence" in instructions
    assert "aggregate a bounded data series" in instructions
    assert "must use code interpreter" in instructions
    assert "different compatible units" in instructions
    assert "do not substitute compute_math for dimensional conversion" in instructions
    assert "never prescribe a fixed tool sequence" in instructions
    assert instructions.index("must use code interpreter") < instructions.index("return exactly one agentic-canvas-plan-v1")


def test_canvas_agent_input_contains_only_the_tutor_authored_semantic_brief() -> None:
    import json

    from services.studio.agent.orchestrator import canvas_agent_input
    from services.studio.canvas_brief import CanvasBriefV1, VisualLearnerContextV1

    brief = CanvasBriefV1.model_validate(
        {
            "version": "canvas-brief-v1",
            "subject_key": "MATH",
            "objective": "Compare fractions as equal parts.",
            "student_request": "Can you help me compare these fractions?",
            "requested_representation": "A fraction model.",
            "facts": ["Three quarters is three equal parts of a whole."],
            "relations": [],
            "quantities": [],
            "desired_student_action": None,
            "must_not_imply": ["Do not state that one fraction is always larger because it has a larger denominator."],
            "source_references": [],
            "locale": "en",
            "direction": "ltr",
        }
    )

    visual_context = VisualLearnerContextV1.model_validate({
        "version": "visual-learner-context-v1", "core_profile": {"age_years": 10, "grade_level": "5"},
        "selected_personal_facts": [{"fact_key": "soccer", "category": "ACTIVITY", "display_statement": "Enjoys soccer."}],
    })
    payload = json.loads(canvas_agent_input(brief, visual_context))

    assert payload == {"canvas_brief": brief.model_dump(mode="json"), "visual_learner_context": visual_context.model_dump(mode="json")}
    assert "student_id" not in json.dumps(payload)
    assert "personal_memory" not in json.dumps(payload)


def test_runtime_skills_are_core_plus_deterministic_authorized_specialists() -> None:
    from services.studio.agent.intelligence import selected_skill_names
    from services.studio.canvas_brief import CanvasBriefV1, VisualLearnerContextV1

    brief = CanvasBriefV1.model_validate({"version": "canvas-brief-v1", "subject_key": "SCIENCE", "objective": "Explain a continuously coupled changing system.", "student_request": "Move the light continuously.", "requested_representation": None, "facts": [], "relations": [], "quantities": [], "desired_student_action": "Move light while the linked geometry updates continuously.", "must_not_imply": [], "source_references": [], "locale": "ar", "direction": "rtl"})
    context = VisualLearnerContextV1.model_validate({"version": "visual-learner-context-v1", "core_profile": {"age_years": 10, "grade_level": "5"}, "selected_personal_facts": []})

    skills = selected_skill_names(brief, context)
    assert {"full-power-routing.md", "visual-composition.md", "tool-selection.md"} <= set(skills)
    assert {"diagrams-and-processes.md", "spatial-interaction.md", "bilingual-layout.md", "age-adaptive-visuals.md"} <= set(skills)
    assert "custom-visual-runtime.md" in skills


def test_model_visible_tool_descriptions_explain_typed_limits_and_create_escalation() -> None:
    from services.studio.agent.orchestrator import build_canvas_agent

    tools = {tool.name: tool.description for tool in build_canvas_agent(api_key="test-only-key", model="gpt-5.6-luna").tools if hasattr(tool, "description")}
    assert "not a continuous simulation" in tools["create_2d_scene"].casefold()
    assert "not simulation" in tools["create_diagram"].casefold()
    assert "cannot invent geometry" in tools["create_math_board"].casefold()
    assert "sandboxed" in tools["create_custom_visual"].casefold()
    assert "instance values" in tools["instantiate_reusable_visual"].casefold()
    from services.studio.agent.orchestrator import CANVAS_AGENT_INSTRUCTIONS
    assert "never use create merely" in CANVAS_AGENT_INSTRUCTIONS.casefold()


def test_agent_trace_records_actual_registered_tool_calls_without_arguments() -> None:
    from types import SimpleNamespace

    from services.studio.agent.orchestrator import (
        CanvasAgentRunContext,
        _compute_math,
        _create_math_board,
    )
    from services.studio.agent.registry import CanvasBlockRegistry

    context = CanvasAgentRunContext(registry=CanvasBlockRegistry())
    wrapper = SimpleNamespace(context=context)

    _compute_math(wrapper, "0.6", "0.45", "COMPARE", "Compare exact decimals.")
    _create_math_board(
        wrapper,
        "decimal-line",
        "Exact decimal positions.",
        "Decimal line",
        "NUMBER_LINE",
        [{"axis": "X", "minimum": "0", "maximum": "1", "step": "1/20"}],
        [],
        [{"id": "comparison", "label": "Comparison", "latex": "0.45 < 0.6", "role": "DERIVED"}],
    )

    assert context.tool_calls == ["compute_math", "create_math_board"]


def test_agents_sdk_wrappers_preserve_rich_typed_block_arguments() -> None:
    from types import SimpleNamespace

    from services.studio.agent.orchestrator import (
        CanvasAgentRunContext,
        _create_2d_scene,
        _create_diagram,
        _create_math_board,
        _create_math_input,
        _create_text_interaction,
    )
    from services.studio.agent.registry import CanvasBlockRegistry

    context = CanvasAgentRunContext(registry=CanvasBlockRegistry())
    wrapper = SimpleNamespace(context=context)
    _create_math_board(
        wrapper,
        "decimal-line",
        "Compare exact decimal positions.",
        "Decimal line",
        "NUMBER_LINE",
        [{"axis": "X", "minimum": "0", "maximum": "1", "step": "1/10"}],
        [{"id": "decimal-a", "label": "0.6", "value": "3/5", "marker_kind": "POINT", "draggable": True}],
        [{"id": "comparison", "label": "Comparison", "latex": r"0.45 < 0.6", "role": "DERIVED"}],
    )
    _create_2d_scene(
        wrapper,
        "force-scene",
        "Show the applied force.",
        "Force scene",
        [{"id": "cart", "label": "Cart", "object_kind": "RECTANGLE", "position": {"x": "40", "y": "50"}, "draggable": False}],
        [],
    )
    _create_diagram(
        wrapper,
        "cycle",
        "Show the repeating cycle.",
        "Cycle",
        "CYCLE",
        "RADIAL",
        [{"id": "stage", "label": "Stage", "node_kind": "PROCESS"}],
        [],
    )
    _create_text_interaction(
        wrapper,
        "sequence",
        "Order the stages.",
        "Sequence",
        "Place the stages in order.",
        "ORDERING",
        [{"id": "first", "text": "First stage", "group_id": None}],
        [],
        [],
    )
    _create_math_input(
        wrapper,
        "answer",
        "Enter an equivalent fraction.",
        "Your answer",
        "Enter a fraction.",
        "",
        ["Use a fraction."],
    )

    blocks = context.registry.blocks()
    assert blocks[0].model_dump()["markers"][0]["value"] == "3/5"
    assert blocks[1].model_dump()["objects"][0]["position"] == {"x": "40", "y": "50"}
    assert blocks[2].model_dump()["topology"] == "CYCLE"
    assert blocks[3].model_dump()["items"][0]["text"] == "First stage"
    assert blocks[4].model_dump()["constraints"] == ["Use a fraction."]


def test_completed_hosted_image_output_is_extracted_as_ephemeral_bytes_only() -> None:
    import base64
    from types import SimpleNamespace

    import pytest

    from services.studio.agent.orchestrator import (
        HostedImageOutputError,
        _extract_hosted_generated_images,
    )

    content = b"\x89PNG\r\nfixture"
    completed = SimpleNamespace(
        new_items=[
            SimpleNamespace(
                raw_item=SimpleNamespace(
                    type="image_generation_call",
                    id="image-call-1",
                    status="completed",
                    result=base64.b64encode(content).decode("ascii"),
                )
            )
        ]
    )
    images = _extract_hosted_generated_images(completed)

    assert len(images) == 1
    assert images[0].temporary_handle == "image-call-1"
    assert images[0].content == content
    assert images[0].content_type == "image/png"
    assert "base64" not in repr(images)

    malformed = SimpleNamespace(
        new_items=[SimpleNamespace(raw_item=SimpleNamespace(
            type="image_generation_call", id="image-call-2", status="completed", result="not-base64!"
        ))]
    )
    with pytest.raises(HostedImageOutputError, match="unsupported"):
        _extract_hosted_generated_images(malformed)


def test_composition_trace_keeps_only_bounded_metadata_for_code_interpreter(
    monkeypatch,
) -> None:
    import asyncio
    import json
    from types import SimpleNamespace

    from services.studio.agent.orchestrator import compose_canvas_scene_with_trace
    from services.studio.agent.tools import create_math_input
    from services.studio.canvas_brief import CanvasBriefV1, VisualLearnerContextV1

    async def fake_run(*args, **kwargs):
        assert kwargs["max_turns"] == 16
        context = kwargs["context"]
        context.registry.accept(create_math_input(
            block_id="calculated-input",
            meaning="Use the validated transformed values.",
            label="Calculated values",
            prompt="Enter the next value.",
            initial_value="",
            constraints=["Use a finite decimal."],
        ))
        return SimpleNamespace(
            final_output={
                "version": "agentic-canvas-plan-v1",
                "objective": "Compare a transformed data series.",
                "subject_key": "MATH",
                "layout": "FOCUS",
                "palette": "AUTO",
                "motion": "NONE",
                "placements": [{"block_id": "calculated-input", "role": "INTERACTION", "order": 0, "span": "NORMAL"}],
                "reveal_order": [],
            },
            new_items=[
                SimpleNamespace(raw_item=SimpleNamespace(
                    type="code_interpreter_call",
                    id="ci-call-1",
                    status="completed",
                    code="print('private raw computation')",
                    outputs=[{"type": "logs", "logs": "private raw result"}],
                )),
            ],
            context_wrapper=SimpleNamespace(usage=SimpleNamespace(
                requests=2,
                input_tokens=101,
                output_tokens=29,
                total_tokens=130,
                input_tokens_details=SimpleNamespace(cached_tokens=11),
            )),
        )

    monkeypatch.setattr("services.studio.agent.orchestrator.Runner.run", fake_run)
    brief = CanvasBriefV1.model_validate({
        "version": "canvas-brief-v1",
        "subject_key": "MATH",
        "objective": "Compare a transformed data series.",
        "student_request": "Help me compare this data.",
        "requested_representation": "A validated numeric interaction.",
        "facts": ["The series requires a multi-step transformation."],
        "relations": [],
        "quantities": [],
        "desired_student_action": "Enter the next transformed value.",
        "must_not_imply": ["Do not expose executable code."],
        "source_references": [],
        "locale": "en",
        "direction": "ltr",
    })

    result = asyncio.run(
            compose_canvas_scene_with_trace(
                brief=brief,
                visual_learner_context=VisualLearnerContextV1.model_validate({"version": "visual-learner-context-v1", "core_profile": {"age_years": 10, "grade_level": "5"}, "selected_personal_facts": []}),
            api_key="test-only-key",
            model="gpt-5.6-luna",
            sdk_trace_id="trace_0123456789abcdef0123456789abcdef",
        )
    )

    assert result.sdk_trace_id == "trace_0123456789abcdef0123456789abcdef"
    assert result.model == "gpt-5.6-luna"
    assert result.usage == {
        "requests": 2,
        "input_tokens": 101,
        "cached_input_tokens": 11,
        "output_tokens": 29,
        "total_tokens": 130,
    }
    assert result.selected_tools == ("code_interpreter",)
    assert result.tool_call_count == 1
    trace = result.tool_calls[0]
    assert trace.name == "code_interpreter"
    assert trace.call_id == "ci-call-1"
    assert trace.status == "completed"
    assert len(trace.input_digest) == len(trace.output_digest) == 64
    assert trace.produced_block_ids == ()
    durable = json.dumps(result.execution_metadata(), sort_keys=True)
    assert "private raw computation" not in durable
    assert "private raw result" not in durable
    assert "code\"" not in durable
    assert "outputs" not in durable


def test_custom_visual_validation_failure_is_retained_as_bounded_agent_metadata() -> None:
    from types import SimpleNamespace

    import pytest

    from services.studio.agent.orchestrator import CanvasAgentRunContext, _create_custom_visual
    from services.studio.agent.registry import CanvasBlockRegistry

    context = CanvasAgentRunContext(registry=CanvasBlockRegistry())
    with pytest.raises(ValueError):
        _create_custom_visual(
            SimpleNamespace(context=context),
            block_id="coupled-lines",
            meaning="Move both points together.",
            label="Coupled slopes",
            source="window.mount=(root)=>{root.textContent='safe'}",
            entities=[],
        )

    assert context.tool_failures == [{
        "tool": "create_custom_visual",
        "reason": '{"code":"CUSTOM_VISUAL_MANIFEST_INVALID","missing_fields":["objective"]}',
    }]


def test_custom_visual_semantic_authoring_builds_the_canonical_package_envelope() -> None:
    from types import SimpleNamespace

    from services.studio.agent.orchestrator import CanvasAgentRunContext, _create_custom_visual
    from services.studio.agent.registry import CanvasBlockRegistry

    context = CanvasAgentRunContext(
        registry=CanvasBlockRegistry(), brief_digest="b" * 64, brief_objective="Compare coupled slopes."
    )
    block = _create_custom_visual(
        SimpleNamespace(context=context),
        block_id="coupled-slopes", meaning="A continuously coupled slope comparison.", label="Coupled slopes",
        source="window.mount=(root,params,bridge)=>{root.textContent=params.label}",
        entities=[{
            "semantic_id": "point-a", "kind": "point", "label": "A",
            "educational_meaning": "A draggable point on a line from the origin.",
            "visible_description": "Point A on the coordinate plane.",
        }],
        interactions=[{
            "semantic_id": "point-a", "action": "MOVE", "meaning": "Move A and update its slope.",
            "value_required": True,
        }],
        parameters={"label": "A"},
    )

    package = context.registry.blocks()[0].package.model_dump(mode="json")
    assert context.registry.blocks()[0].artifact_instance_id == "coupled-slopes-artifact"
    assert package["version"] == "custom-visual-package-v1"
    assert package["manifest"]["brief_digest"] == "b" * 64
    assert package["manifest"]["provenance"] == {"brief_digest": "b" * 64, "runtime_kind": "custom-visual"}
    assert "student_id" not in str(package)


def test_custom_visual_legacy_manifest_envelope_is_canonicalized_not_rejected() -> None:
    from types import SimpleNamespace

    from services.studio.agent.orchestrator import CanvasAgentRunContext, _create_custom_visual
    from services.studio.agent.registry import CanvasBlockRegistry

    context = CanvasAgentRunContext(
        registry=CanvasBlockRegistry(), brief_digest="c" * 64, brief_objective="Compare coupled slopes."
    )
    _create_custom_visual(
        SimpleNamespace(context=context),
        block_id="legacy-coupled", meaning="A coupled slope comparison.", label="Coupled slopes",
        source="window.mount=(root,params,bridge)=>{root.textContent=params.label}",
        semantic_manifest={
            "version": "canvas-semantic-manifest-v1", "objective": "Legacy objective.",
            "representation_summary": "Legacy representation.",
            "entities": [{"semantic_id": "point-a", "kind": "point", "label": "A", "educational_meaning": "A point.", "visible_description": "Point A."}],
            "relations": [], "quantities": [], "presentation_steps": [],
            "interactions": [{"semantic_id": "point-a", "action": "MOVE", "meaning": "Move A.", "value_required": True}],
            "calculated_results": [], "visual_descriptions": [], "current_state_schema": {}, "provenance": {},
        },
        parameters={"label": "A"},
    )

    package = context.registry.blocks()[0].package
    assert package is not None
    assert package.manifest.brief_digest == "c" * 64
    assert package.manifest.objective == "Compare coupled slopes."


def test_create_plan_omission_gets_one_toolless_coherence_repair(monkeypatch) -> None:
    import asyncio
    import json
    from types import SimpleNamespace

    from services.studio.agent.orchestrator import compose_canvas_scene_with_trace
    from services.studio.agent.tools import create_custom_visual, create_math_input
    from services.studio.canvas_brief import CanvasBriefV1, VisualLearnerContextV1

    manifest = {
        "version": "canvas-semantic-manifest-v1", "brief_digest": "a" * 64,
        "objective": "Compare slopes.", "representation_summary": "A coupled slope visual.",
        "entities": [{"semantic_id": "point-a", "kind": "point", "label": "A", "educational_meaning": "A draggable point.", "visible_description": "A point."}],
        "relations": [], "quantities": [], "presentation_steps": [],
        "interactions": [{"semantic_id": "point-a", "action": "MOVE", "meaning": "Move A.", "value_required": True}],
        "calculated_results": [], "visual_descriptions": ["A coupled line."],
        "current_state_schema": {}, "provenance": {"brief_digest": "a" * 64, "runtime_kind": "custom-visual"},
    }
    calls = []

    def result_for(plan):
        return SimpleNamespace(
            final_output=plan, new_items=[],
            context_wrapper=SimpleNamespace(usage=SimpleNamespace(
                requests=1, input_tokens=10, output_tokens=5, total_tokens=15,
                input_tokens_details=SimpleNamespace(cached_tokens=0),
            )),
        )

    async def fake_run(agent, input, **kwargs):
        calls.append((agent, input, kwargs))
        if len(calls) == 1:
            block = kwargs["context"].registry.accept(create_custom_visual(
                block_id="coupled-slopes", meaning="Coupled slopes.", label="Coupled slopes",
                artifact_instance_id="coupled-instance", bridge_nonce="nonce-123", dependencies=["native-svg-v1"],
                source="window.mount=(root)=>{root.textContent='safe'}", manifest=manifest,
                parameter_schema={"type": "object", "properties": {}},
            ))
            kwargs["context"].current_custom_candidate_block_id = block.block_id
            kwargs["context"].registry.accept(create_math_input(
                block_id="typed-answer", meaning="Choose a line.", label="Answer", prompt="Choose.", initial_value="", constraints=[],
            ))
            return result_for({
                "version": "agentic-canvas-plan-v1", "objective": "Compare slopes.", "subject_key": "MATH",
                "layout": "FOCUS", "palette": "COOL", "motion": "NONE",
                "placements": [{"block_id": "typed-answer", "role": "INTERACTION", "order": 0, "span": "NORMAL"}], "reveal_order": [],
            })
        repair = json.loads(input)
        assert agent.tools == []
        assert kwargs["max_turns"] == 1
        assert repair["reason"] == "PLAN_COMPOSITION_INCONSISTENT"
        assert repair["current_custom_candidate_block_id"] == "coupled-slopes"
        assert "source" not in json.dumps(repair)
        return result_for({
            "version": "agentic-canvas-plan-v1", "objective": "Compare slopes.", "subject_key": "MATH",
            "layout": "FOCUS_SUPPORT", "palette": "COOL", "motion": "NONE",
            "placements": [
                {"block_id": "coupled-slopes", "role": "PRIMARY", "order": 0, "span": "FULL"},
                {"block_id": "typed-answer", "role": "INTERACTION", "order": 1, "span": "NORMAL"},
            ], "reveal_order": [],
        })

    monkeypatch.setattr("services.studio.agent.orchestrator.Runner.run", fake_run)
    brief = CanvasBriefV1.model_validate({"version": "canvas-brief-v1", "subject_key": "MATH", "objective": "Compare slopes.", "student_request": "Compare slopes.", "requested_representation": None, "facts": [], "relations": [], "quantities": [], "desired_student_action": None, "must_not_imply": [], "source_references": [], "locale": "en", "direction": "ltr"})
    context = VisualLearnerContextV1.model_validate({"version": "visual-learner-context-v1", "core_profile": {"age_years": 10, "grade_level": "5"}, "selected_personal_facts": []})

    composition = asyncio.run(compose_canvas_scene_with_trace(brief=brief, visual_learner_context=context, api_key="test-only-key", model="gpt-5.6-luna"))

    assert len(calls) == 2
    assert composition.scene.version == "agentic-canvas-scene-v3"
    assert composition.plan_repaired is True
    assert composition.current_custom_candidate_block_id == "coupled-slopes"
    assert composition.plan_block_ids == ("coupled-slopes", "typed-answer")
