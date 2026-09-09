"""The one bounded OpenAI Agents SDK composer for Agentic Canvas scenes."""

from __future__ import annotations

import json

from agents import Agent, OpenAIResponsesModel, RunConfig, Runner, function_tool
from openai import AsyncOpenAI

from services.studio.agent.tools import (
    compute_math,
    convert_units,
    create_2d_scene,
    create_diagram,
    create_math_board,
    create_math_input,
    create_text_interaction,
)
from services.studio.agentic_canvas import AgenticCanvasSceneV1
from services.studio.canvas_brief import CanvasBriefV1


CANVAS_AGENT_INSTRUCTIONS = """You are Lina's single Canvas Agent. The Tutor is the
only teaching and reasoning authority. You receive only a Tutor-authored CanvasBrief
and compose a bounded, declarative visual representation that makes its stated
objective easier to understand. Do not change the objective, infer a different
pedagogical plan, create lesson prose, or make learner judgments.

Use the provided tools when a calculation, unit conversion, or declarative block
will improve the representation. Never describe or output renderer code, CSS, SVG,
browser APIs, components, pixel positions, URLs, prompts for another model, or tool
implementation details. You cannot write Studio state, call the Tutor, access
student records, or delegate to another agent.

Return exactly one agentic-canvas-scene-v1 scene. Every block must come from the
tool allowlist and must preserve the Tutor's subject, objective, quantities, and
must-not-imply constraints. Give each block a stable semantic id and explicit
nullable current_value fields for every element."""


def _agent_tools():
    return [
        function_tool(compute_math),
        function_tool(convert_units),
        function_tool(create_math_board),
        function_tool(create_2d_scene),
        function_tool(create_diagram),
        function_tool(create_text_interaction),
        function_tool(create_math_input),
    ]


def build_canvas_agent(*, api_key: str, model: str, base_url: str | None = None) -> Agent[None]:
    """Build the isolated composer; callers retain all Studio ownership."""
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return Agent(
        name="Lina Canvas Agent",
        instructions=CANVAS_AGENT_INSTRUCTIONS,
        tools=_agent_tools(),
        model=OpenAIResponsesModel(model=model, openai_client=client),
        output_type=AgenticCanvasSceneV1,
    )


def canvas_agent_input(brief: CanvasBriefV1) -> str:
    """Pass only the Tutor's semantic brief, never raw conversation or identity."""
    return json.dumps({"canvas_brief": brief.model_dump(mode="json")}, ensure_ascii=False)


async def compose_canvas_scene(*, brief: CanvasBriefV1, api_key: str, model: str, base_url: str | None = None) -> AgenticCanvasSceneV1:
    """Run one bounded composition without taking Studio ownership."""
    result = await Runner.run(
        build_canvas_agent(api_key=api_key, model=model, base_url=base_url),
        input=canvas_agent_input(brief),
        max_turns=8,
        run_config=RunConfig(
            workflow_name="lina-agentic-canvas-compose",
            trace_include_sensitive_data=False,
        ),
    )
    return AgenticCanvasSceneV1.model_validate(result.final_output)
