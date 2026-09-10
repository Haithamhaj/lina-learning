"""The one bounded OpenAI Agents SDK composer for Agentic Canvas scenes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agents import Agent, OpenAIResponsesModel, RunContextWrapper, RunConfig, Runner, function_tool
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
from services.studio.agent.registry import CanvasBlockRegistry
from services.studio.agentic_canvas import AgenticCanvasPlanV1, AgenticCanvasSceneV1
from services.studio.canvas_brief import CanvasBriefV1


_CANVAS_SKILL_ROOT = Path(__file__).resolve().parents[3] / "runtime" / "canvas-agent"
_CANVAS_SKILL_PACK = "\n\n".join(path.read_text(encoding="utf-8") for path in sorted((_CANVAS_SKILL_ROOT / "skills").glob("*.md")))

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

Return exactly one agentic-canvas-plan-v1. Its placements must refer only to
blocks returned by your create_* tools. Select bounded layout, palette, and
motion semantics; never provide CSS or physical layout. Every selected block
must preserve the Tutor's subject, objective, quantities, and must-not-imply
constraints."""
CANVAS_AGENT_INSTRUCTIONS += "\n\n" + (_CANVAS_SKILL_ROOT / "AGENT.md").read_text(encoding="utf-8") + "\n\n" + _CANVAS_SKILL_PACK


@dataclass
class CanvasAgentRunContext:
    registry: CanvasBlockRegistry


def _block_summary(block):
    return {"block_id": block.block_id, "type": block.type, "meaning": block.meaning}


def _record_block(context: RunContextWrapper[CanvasAgentRunContext], block):
    return _block_summary(context.context.registry.accept(block))


def _create_math_board(context: RunContextWrapper[CanvasAgentRunContext], block_id: str, meaning: str, label: str, expression: str):
    return _record_block(context, create_math_board(block_id=block_id, meaning=meaning, label=label, expression=expression))


def _create_2d_scene(context: RunContextWrapper[CanvasAgentRunContext], block_id: str, meaning: str, label: str):
    return _record_block(context, create_2d_scene(block_id=block_id, meaning=meaning, label=label))


def _create_diagram(context: RunContextWrapper[CanvasAgentRunContext], block_id: str, meaning: str, label: str):
    return _record_block(context, create_diagram(block_id=block_id, meaning=meaning, label=label))


def _create_text_interaction(context: RunContextWrapper[CanvasAgentRunContext], block_id: str, meaning: str, label: str, prompt: str):
    return _record_block(context, create_text_interaction(block_id=block_id, meaning=meaning, label=label, prompt=prompt))


def _create_math_input(context: RunContextWrapper[CanvasAgentRunContext], block_id: str, meaning: str, label: str, initial_value: str = ""):
    return _record_block(context, create_math_input(block_id=block_id, meaning=meaning, label=label, initial_value=initial_value))


def _agent_tools():
    return [
        function_tool(compute_math),
        function_tool(convert_units),
        function_tool(_create_math_board, name_override="create_math_board"),
        function_tool(_create_2d_scene, name_override="create_2d_scene"),
        function_tool(_create_diagram, name_override="create_diagram"),
        function_tool(_create_text_interaction, name_override="create_text_interaction"),
        function_tool(_create_math_input, name_override="create_math_input"),
    ]


def build_canvas_agent(*, api_key: str, model: str, base_url: str | None = None) -> Agent[CanvasAgentRunContext]:
    """Build the isolated composer; callers retain all Studio ownership."""
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return Agent(
        name="Lina Canvas Agent",
        instructions=CANVAS_AGENT_INSTRUCTIONS,
        tools=_agent_tools(),
        model=OpenAIResponsesModel(model=model, openai_client=client),
        output_type=AgenticCanvasPlanV1,
    )


def canvas_agent_input(brief: CanvasBriefV1) -> str:
    """Pass only the Tutor's semantic brief, never raw conversation or identity."""
    return json.dumps({"canvas_brief": brief.model_dump(mode="json")}, ensure_ascii=False)


async def compose_canvas_scene(*, brief: CanvasBriefV1, api_key: str, model: str, base_url: str | None = None) -> AgenticCanvasSceneV1:
    """Run one bounded composition without taking Studio ownership."""
    registry = CanvasBlockRegistry()
    result = await Runner.run(
        build_canvas_agent(api_key=api_key, model=model, base_url=base_url),
        input=canvas_agent_input(brief),
        context=CanvasAgentRunContext(registry=registry),
        max_turns=8,
        run_config=RunConfig(
            workflow_name="lina-agentic-canvas-compose",
            trace_include_sensitive_data=False,
        ),
    )
    return registry.materialize_plan(AgenticCanvasPlanV1.model_validate(result.final_output))
