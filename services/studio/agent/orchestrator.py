"""The one bounded OpenAI Agents SDK composer for Agentic Canvas scenes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from agents import (
    Agent,
    OpenAIResponsesModel,
    RunConfig,
    RunContextWrapper,
    Runner,
    function_tool,
)
from openai import AsyncOpenAI

from services.studio.agent.registry import CanvasBlockRegistry
from services.studio.agent.tools import (
    compute_math,
    convert_units,
    create_2d_scene,
    create_diagram,
    create_math_board,
    create_math_input,
    create_text_interaction,
)
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
    tool_calls: list[str] = field(default_factory=list)

    def record_tool(self, name: str) -> None:
        self.tool_calls.append(name)


@dataclass(frozen=True)
class AgenticCanvasCompositionResult:
    scene: AgenticCanvasSceneV1
    selected_tools: tuple[str, ...]
    tool_call_count: int


def _block_summary(block):
    return {"block_id": block.block_id, "type": block.type, "meaning": block.meaning}


def _record_block(context: RunContextWrapper[CanvasAgentRunContext], block):
    return _block_summary(context.context.registry.accept(block))


def _compute_math(
    context: RunContextWrapper[CanvasAgentRunContext],
    left: str,
    right: str,
    operation: Literal["ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "COMPARE"],
    purpose: str,
):
    context.context.record_tool("compute_math")
    return compute_math(left=left, right=right, operation=operation, purpose=purpose)


def _convert_units(
    context: RunContextWrapper[CanvasAgentRunContext],
    value: str,
    from_unit: str,
    to_unit: str,
):
    context.context.record_tool("convert_units")
    return convert_units(value=value, from_unit=from_unit, to_unit=to_unit)


def _create_math_board(context: RunContextWrapper[CanvasAgentRunContext], block_id: str, meaning: str, label: str, expression: str):
    context.context.record_tool("create_math_board")
    return _record_block(context, create_math_board(block_id=block_id, meaning=meaning, label=label, expression=expression))


def _create_2d_scene(context: RunContextWrapper[CanvasAgentRunContext], block_id: str, meaning: str, label: str):
    context.context.record_tool("create_2d_scene")
    return _record_block(context, create_2d_scene(block_id=block_id, meaning=meaning, label=label))


def _create_diagram(context: RunContextWrapper[CanvasAgentRunContext], block_id: str, meaning: str, label: str):
    context.context.record_tool("create_diagram")
    return _record_block(context, create_diagram(block_id=block_id, meaning=meaning, label=label))


def _create_text_interaction(context: RunContextWrapper[CanvasAgentRunContext], block_id: str, meaning: str, label: str, prompt: str):
    context.context.record_tool("create_text_interaction")
    return _record_block(context, create_text_interaction(block_id=block_id, meaning=meaning, label=label, prompt=prompt))


def _create_math_input(context: RunContextWrapper[CanvasAgentRunContext], block_id: str, meaning: str, label: str, initial_value: str = ""):
    context.context.record_tool("create_math_input")
    return _record_block(context, create_math_input(block_id=block_id, meaning=meaning, label=label, initial_value=initial_value))


def _agent_tools():
    return [
        function_tool(_compute_math, name_override="compute_math"),
        function_tool(_convert_units, name_override="convert_units"),
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


async def compose_canvas_scene_with_trace(*, brief: CanvasBriefV1, api_key: str, model: str, base_url: str | None = None) -> AgenticCanvasCompositionResult:
    """Run one bounded composition and return only accepted tool-call metadata."""
    context = CanvasAgentRunContext(registry=CanvasBlockRegistry())
    result = await Runner.run(
        build_canvas_agent(api_key=api_key, model=model, base_url=base_url),
        input=canvas_agent_input(brief),
        context=context,
        max_turns=8,
        run_config=RunConfig(
            workflow_name="lina-agentic-canvas-compose",
            trace_include_sensitive_data=False,
        ),
    )
    scene = context.registry.materialize_plan(AgenticCanvasPlanV1.model_validate(result.final_output))
    return AgenticCanvasCompositionResult(
        scene=scene,
        selected_tools=tuple(dict.fromkeys(context.tool_calls)),
        tool_call_count=len(context.tool_calls),
    )


async def compose_canvas_scene(*, brief: CanvasBriefV1, api_key: str, model: str, base_url: str | None = None) -> AgenticCanvasSceneV1:
    """Backward-compatible Scene-only boundary for non-worker callers."""
    return (await compose_canvas_scene_with_trace(brief=brief, api_key=api_key, model=model, base_url=base_url)).scene
