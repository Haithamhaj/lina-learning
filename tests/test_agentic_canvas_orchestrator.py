from __future__ import annotations


def test_single_canvas_agent_uses_only_the_bounded_local_tool_registry() -> None:
    from services.studio.agent.orchestrator import build_canvas_agent
    from services.studio.agent.tools import tool_names
    from services.studio.agentic_canvas import AgenticCanvasPlanV1

    agent = build_canvas_agent(api_key="test-only-key", model="gpt-5.6-luna")

    assert agent.handoffs == []
    assert tuple(tool.name for tool in agent.tools) == tool_names()
    assert agent.output_type is AgenticCanvasPlanV1
    assert "Tutor" in agent.instructions
    assert "write Studio" in agent.instructions


def test_canvas_agent_input_contains_only_the_tutor_authored_semantic_brief() -> None:
    import json

    from services.studio.agent.orchestrator import canvas_agent_input
    from services.studio.canvas_brief import CanvasBriefV1

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

    payload = json.loads(canvas_agent_input(brief))

    assert payload == {"canvas_brief": brief.model_dump(mode="json")}
    assert "student_id" not in json.dumps(payload)


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
    _create_math_board(wrapper, "decimal-line", "Exact decimal positions.", "Decimal line", "0.45 < 0.6")

    assert context.tool_calls == ["compute_math", "create_math_board"]
