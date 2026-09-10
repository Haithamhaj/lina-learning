"""The one bounded OpenAI Agents SDK composer for Agentic Canvas scenes."""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from agents import (
    Agent,
    CodeInterpreterTool,
    ImageGenerationTool,
    OpenAIResponsesModel,
    RunConfig,
    RunContextWrapper,
    Runner,
    function_tool,
)
from agents.tracing import gen_trace_id
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
from services.studio.agentic_canvas import (
    DiagramEdgeV1,
    DiagramNodeV1,
    MathAxisV1,
    MathExpressionV1,
    MathMarkerV1,
    SpatialObjectV1,
    SpatialRelationV1,
    TextGroupV1,
    TextItemV1,
    TextRelationV1,
)
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
    generated_images: tuple["HostedGeneratedImage", ...] = ()
    sdk_trace_id: str | None = None
    model: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    tool_calls: tuple["AgentToolCallTrace", ...] = ()

    def execution_metadata(self) -> dict[str, object]:
        """Return the bounded durable Agent run envelope, never raw inputs/results."""

        return {
            "sdk_trace_id": self.sdk_trace_id,
            "model": self.model,
            "usage": dict(self.usage),
            "selected_tools": list(self.selected_tools),
            "tool_call_count": self.tool_call_count,
            "tool_calls": [call.as_dict() for call in self.tool_calls],
        }


@dataclass(frozen=True, slots=True)
class AgentToolCallTrace:
    name: str
    call_id: str
    status: str
    input_digest: str
    output_digest: str
    produced_block_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "call_id": self.call_id,
            "status": self.status,
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
            "produced_block_ids": list(self.produced_block_ids),
        }


class HostedImageOutputError(ValueError):
    """The SDK exposed an image output that cannot cross Lina's asset boundary."""


@dataclass(frozen=True, slots=True)
class HostedGeneratedImage:
    temporary_handle: str
    content: bytes = field(repr=False)
    content_type: Literal["image/png"] = "image/png"


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


def _create_math_board(
    context: RunContextWrapper[CanvasAgentRunContext],
    block_id: str,
    meaning: str,
    label: str,
    board_kind: Literal["NUMBER_LINE", "CARTESIAN", "PLOT"],
    axes: list[MathAxisV1],
    markers: list[MathMarkerV1],
    expressions: list[MathExpressionV1],
):
    context.context.record_tool("create_math_board")
    return _record_block(context, create_math_board(
        block_id=block_id,
        meaning=meaning,
        label=label,
        board_kind=board_kind,
        axes=axes,
        markers=markers,
        expressions=expressions,
    ))


def _create_2d_scene(
    context: RunContextWrapper[CanvasAgentRunContext],
    block_id: str,
    meaning: str,
    label: str,
    objects: list[SpatialObjectV1],
    relations: list[SpatialRelationV1],
):
    context.context.record_tool("create_2d_scene")
    return _record_block(context, create_2d_scene(
        block_id=block_id,
        meaning=meaning,
        label=label,
        objects=objects,
        relations=relations,
    ))


def _create_diagram(
    context: RunContextWrapper[CanvasAgentRunContext],
    block_id: str,
    meaning: str,
    label: str,
    topology: Literal["SEQUENCE", "CYCLE", "FLOW", "CAUSE_EFFECT", "COMPARISON", "HIERARCHY", "SYSTEM", "CONCEPT_MAP"],
    layout: Literal["HORIZONTAL", "VERTICAL", "RADIAL", "TREE", "GRID", "AUTO"],
    nodes: list[DiagramNodeV1],
    edges: list[DiagramEdgeV1],
):
    context.context.record_tool("create_diagram")
    return _record_block(context, create_diagram(
        block_id=block_id,
        meaning=meaning,
        label=label,
        topology=topology,
        layout=layout,
        nodes=nodes,
        edges=edges,
    ))


def _create_text_interaction(
    context: RunContextWrapper[CanvasAgentRunContext],
    block_id: str,
    meaning: str,
    label: str,
    prompt: str,
    interaction_family: Literal["ORDERING", "MATCHING", "CLASSIFICATION", "GROUPING", "HIGHLIGHT", "ANNOTATION", "RELATION", "TOKEN_MANIPULATION"],
    items: list[TextItemV1],
    groups: list[TextGroupV1],
    relations: list[TextRelationV1],
):
    context.context.record_tool("create_text_interaction")
    return _record_block(context, create_text_interaction(
        block_id=block_id,
        meaning=meaning,
        label=label,
        prompt=prompt,
        interaction_family=interaction_family,
        items=items,
        groups=groups,
        relations=relations,
    ))


def _create_math_input(
    context: RunContextWrapper[CanvasAgentRunContext],
    block_id: str,
    meaning: str,
    label: str,
    prompt: str,
    initial_value: str,
    constraints: list[str],
):
    context.context.record_tool("create_math_input")
    return _record_block(context, create_math_input(
        block_id=block_id,
        meaning=meaning,
        label=label,
        prompt=prompt,
        initial_value=initial_value,
        constraints=constraints,
    ))


def _agent_tools():
    return [
        function_tool(_compute_math, name_override="compute_math"),
        function_tool(_convert_units, name_override="convert_units"),
        function_tool(_create_math_board, name_override="create_math_board"),
        function_tool(_create_2d_scene, name_override="create_2d_scene"),
        function_tool(_create_diagram, name_override="create_diagram"),
        function_tool(_create_text_interaction, name_override="create_text_interaction"),
        function_tool(_create_math_input, name_override="create_math_input"),
        ImageGenerationTool(tool_config={
            "type": "image_generation",
            "action": "generate",
            "background": "opaque",
            "moderation": "auto",
            "output_format": "png",
            "partial_images": 0,
            "quality": "low",
        }),
        CodeInterpreterTool(tool_config={
            "type": "code_interpreter",
            "container": {"type": "auto"},
        }),
    ]


_HOSTED_IMAGE_HANDLE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,127}$")
_MAX_HOSTED_IMAGE_BASE64_CHARS = 28_000_000
_SAFE_CALL_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _value(item: object, name: str, default: Any = None) -> Any:
    return item.get(name, default) if isinstance(item, dict) else getattr(item, name, default)


def _metadata_digest(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _bounded_usage(result: object) -> dict[str, int]:
    usage = getattr(getattr(result, "context_wrapper", None), "usage", None)
    details = getattr(usage, "input_tokens_details", None)
    return {
        "requests": int(getattr(usage, "requests", 0) or 0),
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "cached_input_tokens": int(getattr(details, "cached_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def _extract_tool_call_trace(result: object) -> tuple[AgentToolCallTrace, ...]:
    """Reduce SDK items to IDs, statuses and digests; raw code/results never leave this call."""

    outputs: dict[str, object] = {}
    for item in getattr(result, "new_items", ()):
        raw = getattr(item, "raw_item", None)
        if _value(raw, "type") == "function_call_output":
            call_id = _value(raw, "call_id") or _value(raw, "id")
            if isinstance(call_id, str):
                outputs[call_id] = getattr(item, "output", _value(raw, "output"))

    calls: list[AgentToolCallTrace] = []
    for item in getattr(result, "new_items", ()):
        raw = getattr(item, "raw_item", None)
        raw_type = _value(raw, "type")
        if raw_type not in {"function_call", "image_generation_call", "code_interpreter_call"}:
            continue
        call_id = _value(raw, "call_id") or _value(raw, "id")
        if not isinstance(call_id, str) or _SAFE_CALL_ID.fullmatch(call_id) is None:
            raise HostedImageOutputError("SDK tool call identity is missing or invalid.")
        if raw_type == "function_call":
            name = _value(raw, "name")
            if not isinstance(name, str) or name not in _agent_function_tool_names():
                raise HostedImageOutputError("SDK function tool identity is outside the Canvas allowlist.")
            raw_input = _value(raw, "arguments", "")
            raw_output = outputs.get(call_id, "")
            produced = _produced_block_ids(raw_output)
        elif raw_type == "image_generation_call":
            name = "image_generation"
            raw_input = {"quality": _value(raw, "quality"), "size": _value(raw, "size")}
            raw_output = _value(raw, "result", "")
            produced = ()
        else:
            name = "code_interpreter"
            raw_input = _value(raw, "code", "")
            raw_output = _value(raw, "outputs", ())
            produced = ()
        calls.append(AgentToolCallTrace(
            name=name,
            call_id=call_id,
            status=str(_value(raw, "status", "completed")),
            input_digest=_metadata_digest(raw_input),
            output_digest=_metadata_digest(raw_output),
            produced_block_ids=produced,
        ))
    return tuple(calls)


def _agent_function_tool_names() -> frozenset[str]:
    return frozenset({
        "compute_math", "convert_units", "create_math_board", "create_2d_scene",
        "create_diagram", "create_text_interaction", "create_math_input",
    })


def _produced_block_ids(output: object) -> tuple[str, ...]:
    value = output
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return ()
    block_id = _value(value, "block_id")
    return (block_id,) if isinstance(block_id, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", block_id) else ()


def _extract_hosted_generated_images(result: object) -> tuple[HostedGeneratedImage, ...]:
    """Extract the one documented completed PNG result, rejecting every other shape."""

    calls: list[object] = []
    for item in getattr(result, "new_items", ()):
        raw = getattr(item, "raw_item", None)
        raw_type = raw.get("type") if isinstance(raw, dict) else getattr(raw, "type", None)
        if raw_type == "image_generation_call":
            calls.append(raw)
    if not calls:
        return ()
    if len(calls) != 1:
        raise HostedImageOutputError("Hosted image output is unsupported: exactly one completed image is required.")
    call = calls[0]
    handle, status, encoded = _value(call, "id"), _value(call, "status"), _value(call, "result")
    if (
        status != "completed"
        or not isinstance(handle, str)
        or _HOSTED_IMAGE_HANDLE.fullmatch(handle) is None
        or not isinstance(encoded, str)
        or not encoded
        or len(encoded) > _MAX_HOSTED_IMAGE_BASE64_CHARS
    ):
        raise HostedImageOutputError("Hosted image output is unsupported or incomplete.")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HostedImageOutputError("Hosted image output is unsupported or malformed.") from exc
    if not content:
        raise HostedImageOutputError("Hosted image output is unsupported or empty.")
    return (HostedGeneratedImage(temporary_handle=handle, content=content),)


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


async def compose_canvas_scene_with_trace(*, brief: CanvasBriefV1, api_key: str, model: str, base_url: str | None = None, sdk_trace_id: str | None = None) -> AgenticCanvasCompositionResult:
    """Run one bounded composition and return only accepted tool-call metadata."""
    context = CanvasAgentRunContext(registry=CanvasBlockRegistry())
    trace_id = sdk_trace_id or gen_trace_id()
    result = await Runner.run(
        build_canvas_agent(api_key=api_key, model=model, base_url=base_url),
        input=canvas_agent_input(brief),
        context=context,
        max_turns=8,
        run_config=RunConfig(
            workflow_name="lina-agentic-canvas-compose",
            trace_id=trace_id,
            trace_include_sensitive_data=False,
        ),
    )
    scene = context.registry.materialize_plan(AgenticCanvasPlanV1.model_validate(result.final_output))
    generated_images = _extract_hosted_generated_images(result)
    tool_calls = _extract_tool_call_trace(result)
    selected_tools = tuple(dict.fromkeys(call.name for call in tool_calls))
    return AgenticCanvasCompositionResult(
        scene=scene,
        selected_tools=selected_tools,
        tool_call_count=len(tool_calls),
        generated_images=generated_images,
        sdk_trace_id=trace_id,
        model=model,
        usage=_bounded_usage(result),
        tool_calls=tool_calls,
    )


async def compose_canvas_scene(*, brief: CanvasBriefV1, api_key: str, model: str, base_url: str | None = None) -> AgenticCanvasSceneV1:
    """Backward-compatible Scene-only boundary for non-worker callers."""
    composition = await compose_canvas_scene_with_trace(brief=brief, api_key=api_key, model=model, base_url=base_url)
    if composition.generated_images:
        raise HostedImageOutputError("Hosted images require the owned Studio asset adoption boundary.")
    return composition.scene
