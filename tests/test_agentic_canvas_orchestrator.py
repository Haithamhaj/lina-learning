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
    schemas = {
        tool.name: getattr(tool, "params_json_schema", None)
        for tool in agent.tools
    }
    assert set(schemas["create_math_board"]["properties"]) >= {"axes", "markers", "expressions"}
    assert set(schemas["create_2d_scene"]["properties"]) >= {"objects", "relations"}
    assert set(schemas["create_diagram"]["properties"]) >= {"nodes", "edges"}
    assert set(schemas["create_text_interaction"]["properties"]) >= {"items", "groups", "relations"}


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
