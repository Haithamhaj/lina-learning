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
    RunHooks,
    function_tool,
)
from agents.tracing import gen_trace_id
from openai import AsyncOpenAI

from services.studio.agent.registry import CanvasBlockRegistry, PlanCompositionInconsistencyError
from services.studio.agent.tools import (
    compute_math,
    convert_units,
    create_2d_scene,
    create_diagram,
    create_math_board,
    create_math_input,
    create_custom_visual,
    create_reused_custom_visual,
    create_text_interaction,
)
from services.studio.agentic_canvas import AgenticCanvasPlanV1, AgenticCanvasScene
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
from services.studio.canvas_brief import CanvasBriefV1, VisualLearnerContextV1
from services.studio.full_power_canvas import (
    CanvasPresentationStepV1,
    CanvasSemanticEntityV1,
    CanvasSemanticInteractionV1,
    CanvasSemanticManifestDraftV1,
    CanvasSemanticQuantityV1,
    CanvasSemanticRelationV1,
    CanvasSemanticManifestV1,
    CustomVisualSecurityError,
    CustomVisualInteractionLayoutError,
)
from services.studio.agent.intelligence import assemble_canvas_intelligence

_CANVAS_SKILL_ROOT = Path(__file__).resolve().parents[3] / "runtime" / "canvas-agent"

CANVAS_AGENT_INSTRUCTIONS = """You are Lina's Full-Power Canvas Agent. The Tutor is the
only teaching and reasoning authority. You receive only a Tutor-authored CanvasBrief
and a bounded Visual Learner Context. Your mission is to make the approved educational
meaning perceptible, explorable, manipulable, and understandable. Do not change
academic truth, infer learner traits, create lesson prose, or change the objective.

Priority: educational truth and must-not-imply constraints; learner understanding;
representational adequacy; visual and interaction quality; reuse opportunity; then
latency and cost. A capability is adequate only when it preserves the material
structure, interaction, dynamic dependency, fidelity, simultaneous comparison, and
explanatory quality of the learning job. Minimum semantic complexity means the simplest
fully adequate representation, never the weakest visual path.

Use the provided tools when a calculation, unit conversion, or declarative block
will improve the representation. Never describe or output renderer code, CSS, SVG,
browser APIs, components, pixel positions, URLs, prompts for another model, or tool
implementation details. You cannot write Studio state, call the Tutor, access
student records, or delegate to another agent.

Choose tools only from the semantic need in the CanvasBrief; never prescribe a fixed tool sequence.
If the brief requires a long bounded recurrence, repeated
transformation, or an aggregate a bounded data series beyond one ordinary exact
arithmetic operation, you must use Code Interpreter and keep its raw code and
output transient. If compatible physical quantities use different compatible units, use
convert_units rather than compute_math to establish dimensional truth; do not substitute compute_math for dimensional conversion. If the
brief requires one original illustrative image whose organic or irregular detail
cannot be represented by typed geometric or diagram primitives, use one Image Generation call. Do not replace that requested illustration with typed primitives.

Return exactly one agentic-canvas-plan-v1. Its placements must refer only to
blocks returned by your create_* tools. Select bounded layout, palette, and
motion semantics. Never provide implementation detail except as the source
argument to create_custom_visual when CREATE is genuinely required. That is
the only approved custom-code boundary: source defines window.mount, receives
facts only through parameters, and emits only declared semantic actions via
the supplied bridge. Never put source code in the final plan.

Choose REUSE when a validated artifact already fits. Choose ADAPT only for a bounded
generalized artifact change, never ordinary instance values. Choose CREATE as a normal
first-class route when typed/reusable capability would materially lose meaningful
structure, interaction, coupled/dynamic behavior, fidelity, layered composition, or
explanatory quality. Typed blocks are fast paths, not a ceiling. Every selected block must preserve the Tutor's subject,
objective, quantities, and must-not-imply constraints. Never use CREATE merely to
decorate a lesson, combine routine typed blocks, or replace an exact bounded visual
that already preserves the learning job."""
CANVAS_AGENT_INSTRUCTIONS += """
Search the reusable registry before CREATE when a reusable visual might fit.
Registry search returns only semantic summaries. For CREATE, pass semantic entities,
relations, quantities, interactions, and values as structured tool arguments; do not
pass a semantic_manifest envelope. The system deterministically constructs its
canonical Manifest, package envelope, provenance, instance identity, and parameter
schema. Use mode REUSE for an unchanged structure and ADAPT only when a new
version is needed. The source itself is never placed in a plan or narrative."""


@dataclass
class CanvasAgentRunContext:
    registry: CanvasBlockRegistry
    brief_digest: str = "0" * 64
    tool_calls: list[str] = field(default_factory=list)
    # These summaries are supplied by the application-owned registry adapter.
    # They contain reusable definitions only: no student identity, history, or
    # previously bound learner values.  Source stays internal to the tool.
    reusable_visuals: dict[str, dict[str, object]] = field(default_factory=dict)
    reusable_selections: list[dict[str, object]] = field(default_factory=list)
    tool_failures: list[dict[str, str]] = field(default_factory=list)
    # Set only after a CREATE package has passed the bounded package, manifest,
    # and registry admission path. A later valid CREATE supersedes this ID.
    current_custom_candidate_block_id: str | None = None
    model_turns: list[dict[str, object]] = field(default_factory=list)
    brief_objective: str = ""
    create_route_attempted: bool = False
    custom_attempt_count: int = 0

    def record_tool(self, name: str) -> None:
        self.tool_calls.append(name)

    def record_tool_failure(self, name: str, reason: str) -> None:
        self.tool_failures.append({"tool": name, "reason": reason[:320]})


@dataclass(frozen=True)
class AgenticCanvasCompositionResult:
    scene: AgenticCanvasScene
    selected_tools: tuple[str, ...]
    tool_call_count: int
    generated_images: tuple["HostedGeneratedImage", ...] = ()
    sdk_trace_id: str | None = None
    model: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    tool_calls: tuple["AgentToolCallTrace", ...] = ()
    reusable_selections: tuple[dict[str, object], ...] = ()
    tool_failures: tuple[dict[str, str], ...] = ()
    registered_block_ids: tuple[str, ...] = ()
    plan_block_ids: tuple[str, ...] = ()
    current_custom_candidate_block_id: str | None = None
    plan_repaired: bool = False
    model_turns: tuple[dict[str, object], ...] = ()

    def execution_metadata(self) -> dict[str, object]:
        """Return the bounded durable Agent run envelope, never raw inputs/results."""

        result = {
            "sdk_trace_id": self.sdk_trace_id,
            "model": self.model,
            "usage": dict(self.usage),
            "selected_tools": list(self.selected_tools),
            "tool_call_count": self.tool_call_count,
            "tool_calls": [call.as_dict() for call in self.tool_calls],
        }
        if self.reusable_selections:
            result["reusable_selections"] = [dict(selection) for selection in self.reusable_selections]
        if self.tool_failures:
            result["tool_failures"] = [dict(failure) for failure in self.tool_failures]
        if self.registered_block_ids:
            result["registered_block_ids"] = list(self.registered_block_ids)
        if self.plan_block_ids:
            result["plan_block_ids"] = list(self.plan_block_ids)
        if self.current_custom_candidate_block_id is not None:
            result["current_custom_candidate_block_id"] = self.current_custom_candidate_block_id
        if self.plan_repaired:
            result["plan_repaired"] = True
        if self.model_turns:
            result["model_turns"] = [dict(turn) for turn in self.model_turns]
        return result


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


class CustomVisualCandidateMissingError(ValueError):
    """CREATE was selected but its bounded authoring attempts produced no package."""

    code = "CUSTOM_VISUAL_CANDIDATE_MISSING"

    def __init__(self, *, tool_failures: list[dict[str, str]], model_turns: list[dict[str, object]]) -> None:
        super().__init__("CUSTOM_VISUAL_CANDIDATE_MISSING")
        # These are bounded validation categories/paths only.  They deliberately
        # exclude generated source, prompts, and model prose.
        self.tool_failures = tuple(dict(item) for item in tool_failures[-2:])
        self.model_turns = tuple(dict(item) for item in model_turns[-16:])


@dataclass(frozen=True, slots=True)
class HostedGeneratedImage:
    temporary_handle: str
    content: bytes = field(repr=False)
    content_type: Literal["image/png"] = "image/png"


class CanvasCompositionRunHooks(RunHooks[CanvasAgentRunContext]):
    """Persist bounded phase evidence without retaining prompts, code, or model prose."""

    async def on_llm_start(self, context, agent, system_prompt, input_items) -> None:
        context.context.model_turns.append({
            "turn": len(context.context.model_turns) + 1,
            "tool_calls": [],
            "produced_block_ids": [],
            "current_custom_candidate_block_id": context.context.current_custom_candidate_block_id,
            "final_plan_validation": "PENDING",
        })

    async def on_tool_end(self, context, agent, tool, result) -> None:
        if not context.context.model_turns:
            return
        turn = context.context.model_turns[-1]
        calls = turn["tool_calls"]
        assert isinstance(calls, list)
        calls.append(tool.name)
        produced = _produced_block_ids(result)
        if produced:
            block_ids = turn["produced_block_ids"]
            assert isinstance(block_ids, list)
            block_ids.extend(produced)
        turn["current_custom_candidate_block_id"] = context.context.current_custom_candidate_block_id

    async def on_agent_end(self, context, agent, output) -> None:
        if context.context.model_turns:
            context.context.model_turns[-1]["final_plan_validation"] = "PLAN_OUTPUT_RECEIVED"


def _record_final_plan_validation(
    context: CanvasAgentRunContext,
    result: str,
    *,
    repair_reason: str | None = None,
) -> None:
    if not context.model_turns:
        return
    context.model_turns[-1]["final_plan_validation"] = result
    if repair_reason is not None:
        context.model_turns[-1]["repair_reason"] = repair_reason


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
    """Establish one exact arithmetic/comparison truth; not unit conversion, simulation, or visual composition. Escalate materially complex transforms to Code Interpreter."""
    context.context.record_tool("compute_math")
    return compute_math(left=left, right=right, operation=operation, purpose=purpose)


def _convert_units(
    context: RunContextWrapper[CanvasAgentRunContext],
    value: str,
    from_unit: str,
    to_unit: str,
):
    """Establish compatible-unit conversion truth; not a scientific simulation. Use before showing quantities in different units."""
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
    """Create a typed exact number-line, Cartesian, or plot visual. It cannot invent geometry or model coupled continuous behavior; escalate inadequate interaction to reusable visual or CREATE."""
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
    """Create discrete objects, logical positions, and finite relations. It is not a continuous simulation or coupled-geometry engine; escalate those learning jobs to reusable visual or CREATE."""
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
    """Create finite typed semantic topology. It is not simulation, free-form spatial modeling, or arbitrary interaction; escalate when those are educationally material."""
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
    """Create bounded ordering, matching, grouping, annotation, or relation interaction. It is not a free-form linguistic visualization; escalate richer required structure."""
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
    """Create bounded learner notation entry. It does not explain geometry, magnitude, or simulation; pair with another representation only when useful."""
    context.context.record_tool("create_math_input")
    return _record_block(context, create_math_input(
        block_id=block_id,
        meaning=meaning,
        label=label,
        prompt=prompt,
        initial_value=initial_value,
        constraints=constraints,
    ))


def _create_custom_visual(
    context: RunContextWrapper[CanvasAgentRunContext],
    block_id: str,
    meaning: str,
    label: str,
    source: str,
    entities: list[CanvasSemanticEntityV1] | None = None,
    relations: list[CanvasSemanticRelationV1] | None = None,
    quantities: list[CanvasSemanticQuantityV1] | None = None,
    interactions: list[CanvasSemanticInteractionV1] | None = None,
    presentation_steps: list[CanvasPresentationStepV1] | None = None,
    visual_descriptions: list[str] | None = None,
    current_state_schema: dict[str, str] | None = None,
    parameters: dict[str, str | int | float | bool] | None = None,
    # Compatibility only for a previously advertised authoring shape.  Keep this
    # untyped at the SDK boundary: the system extracts the model-authored fields
    # and builds the strict canonical Manifest below.  A Draft model here would
    # reject legacy/internal boilerplate before canonicalization can run.
    semantic_manifest: dict[str, object] | None = None,
):
    """CREATE a sandboxed custom visual from semantic entities, actions, and source. Submit source as one minified valid JSON string: use single-quoted JavaScript literals and no literal newlines or double quotes in source, so the tool-call JSON stays valid. Every semantic_id used by relations, quantities, or interactions must first appear in entities; use entity IDs, never action/step IDs. Use native local state and the supplied semantic bridge only: no fetch, network, storage, cookies, parent window, imports, or application APIs."""
    context.context.record_tool("create_custom_visual")
    context.context.create_route_attempted = True
    try:
        # Compatibility for an already-issued model call shape. The new
        # authoring contract exposes individual semantic fields; if a model
        # still supplies the old envelope, extract only its authored semantic
        # content and rebuild the canonical manifest below.
        if semantic_manifest is not None:
            legacy = dict(semantic_manifest)
            # Do not strictly validate the old envelope first: canonicalization
            # intentionally supplies minimal entity records for relation/action
            # targets that the model named but did not repeat as boilerplate.
            entities = entities or legacy.get("entities", [])
            relations = relations or legacy.get("relations", [])
            quantities = quantities or legacy.get("quantities", [])
            interactions = interactions or legacy.get("interactions", [])
            presentation_steps = presentation_steps or legacy.get("presentation_steps", [])
            visual_descriptions = visual_descriptions or legacy.get("visual_descriptions", [])
            current_state_schema = current_state_schema or legacy.get("current_state_schema", {})
        validated_manifest = _canonical_custom_manifest(
            objective=context.context.brief_objective,
            meaning=meaning,
            entities=[CanvasSemanticEntityV1.model_validate(item) for item in entities or []],
            relations=[CanvasSemanticRelationV1.model_validate(item) for item in relations or []],
            quantities=[CanvasSemanticQuantityV1.model_validate(item) for item in quantities or []],
            interactions=[CanvasSemanticInteractionV1.model_validate(item) for item in interactions or []],
            presentation_steps=[CanvasPresentationStepV1.model_validate(item) for item in presentation_steps or []],
            visual_descriptions=visual_descriptions or [],
            current_state_schema=current_state_schema or {},
            brief_digest=context.context.brief_digest,
        )
    except (TypeError, ValueError) as exc:
        context.context.record_tool_failure(
            "create_custom_visual",
            json.dumps(_custom_visual_error_payload(exc), separators=(",", ":")),
        )
        raise CustomVisualAuthoringError(_custom_visual_error_payload(exc)) from exc
    try:
        summary = _record_block(context, create_custom_visual(
            block_id=block_id,
            meaning=meaning,
            label=label,
            artifact_instance_id=f"{block_id}-artifact",
            bridge_nonce=sha256(f"{context.context.brief_digest}:{block_id}".encode()).hexdigest()[:32],
            source=source,
            dependencies=["native-svg-v1"],
            manifest=validated_manifest,
            parameter_schema=_parameter_schema(parameters or {}),
            parameters=parameters or {},
        ))
        # A later successful CREATE intentionally replaces this run-local
        # candidate. It is still registry-owned; finalization must reference
        # this exact canonical block rather than inventing an ID.
        context.context.current_custom_candidate_block_id = summary["block_id"]
        return summary
    except (TypeError, ValueError) as exc:
        payload = _custom_visual_error_payload(exc)
        context.context.record_tool_failure("create_custom_visual", json.dumps(payload, separators=(",", ":")))
        raise CustomVisualAuthoringError(payload) from exc


def _custom_visual_tool_error(
    context: RunContextWrapper[CanvasAgentRunContext], error: Exception
) -> str:
    """Retain a bounded reason when SDK argument validation rejects CREATE first."""
    context.context.create_route_attempted = True
    context.context.custom_attempt_count += 1
    payload = _custom_visual_error_payload(error)
    context.context.record_tool_failure("create_custom_visual", json.dumps(payload, separators=(",", ":")))
    return json.dumps(payload, separators=(",", ":"))


class CustomVisualAuthoringError(ValueError):
    """A safe, bounded validation response for one custom-package repair."""

    def __init__(self, payload: dict[str, object]) -> None:
        super().__init__(str(payload["code"]))
        self.payload = payload


def _custom_visual_error_payload(error: Exception) -> dict[str, object]:
    """Expose repairable contract failures without source or internal runtime data."""
    if isinstance(error, CustomVisualAuthoringError):
        return dict(error.payload)
    if "invalid json input for tool" in str(error).casefold():
        payload: dict[str, object] = {
            "code": "CUSTOM_VISUAL_ARGUMENT_ENCODING_INVALID",
            "repair": (
                "Resubmit the same source and semantic fields as valid JSON. Keep source on one "
                "minified line, with single-quoted JavaScript literals and no literal double quotes or newlines. "
                "Do not restart composition."
            ),
        }
        # Preserve parser location, never the raw generated source. This tells a
        # bounded authoring repair whether the call was truncated or malformed.
        current: BaseException | None = error
        while current is not None:
            if isinstance(current, json.JSONDecodeError):
                payload["json_error"] = (
                    f"{current.msg} at line {current.lineno} column {current.colno}"
                )
                break
            current = current.__cause__ or current.__context__
        return payload
    if isinstance(error, CustomVisualSecurityError):
        message = str(error).casefold()
        if "semantic_interaction_binding_invalid" in message:
            return {
                "code": "SEMANTIC_INTERACTION_BINDING_INVALID",
                "repair": "Emit each declared bridge semantic_id as its exact literal Manifest ID; do not use a dynamic variable for semantic_id.",
            }
        capability = "unknown"
        for name in ("fetch", "xmlhttprequest", "websocket", "cookie", "storage", "window.parent", "import"):
            if name in message:
                capability = name
                break
        return {"code": "CUSTOM_VISUAL_FORBIDDEN_API", "forbidden_capability": capability}
    if isinstance(error, CustomVisualInteractionLayoutError):
        return {
            "code": "CUSTOM_VISUAL_INTERACTION_CONTROL_NOT_RENDERABLE",
            "repair": "Mount declared controls in an HTML container or implement visible SVG-native controls; do not append HTML controls to an SVG parent.",
        }
    fields = _validation_locations(error)
    payload: dict[str, object] = {
        "code": "CUSTOM_VISUAL_MANIFEST_INVALID",
        "missing_fields": fields or ["semantic_manifest"],
    }
    if not fields:
        # ValueError validators do not expose Pydantic locations. Their message
        # is still an actionable semantic constraint and contains no source or
        # learner data, unlike the generated package itself.
        payload["repair"] = str(error)[:280]
    return payload


def _manifest_failure_reason(error: Exception) -> str:
    """Persist validation paths, never model content or generated source."""
    locations = _validation_locations(error)
    suffix = ", ".join(locations)
    return (
        "Custom visual manifest has invalid required fields: " + suffix
        if suffix else f"Custom visual manifest must be a bounded Semantic Manifest object ({type(error).__name__})."
    )


def _validation_locations(error: Exception) -> list[str]:
    details = getattr(error, "errors", None)
    if not callable(details):
        return []
    locations: list[str] = []
    for item in details(include_input=False, include_url=False)[:8]:
        location = item.get("loc")
        if isinstance(location, (list, tuple)):
            path = ".".join(str(part) for part in location)
            if not path:
                message = str(item.get("msg", "")).casefold()
                path = (
                    "semantic_manifest.references"
                    if "reference declared entities" in message
                    else "semantic_manifest"
                )
            locations.append(path)
    return locations


def _search_reusable_visuals(
    context: RunContextWrapper[CanvasAgentRunContext],
    query: str,
):
    """Search at most five validated reusable visual summaries before plausible CREATE. A match is not automatically adequate and implementation source never leaves the registry."""
    context.context.record_tool("search_reusable_visuals")
    words = {word for word in query.lower().split() if word}
    candidates = sorted(
        context.context.reusable_visuals.items(),
        key=lambda item: len(words & set((str(item[1].get("semantic_purpose", "")) + " " + str(item[1].get("stable_slug", ""))).lower().replace("-", " ").split())),
        reverse=True,
    )[:5]
    return [
        {
            "version_id": version_id,
            "stable_slug": str(value["stable_slug"]),
            "semantic_purpose": str(value["semantic_purpose"]),
            "runtime_kind": str(value["runtime_kind"]),
            "parameter_schema": value["parameter_schema"],
        }
        for version_id, value in candidates
    ]


def _instantiate_reusable_visual(
    context: RunContextWrapper[CanvasAgentRunContext],
    version_id: str,
    block_id: str,
    meaning: str,
    label: str,
    artifact_instance_id: str,
    bridge_nonce: str,
    parameters: dict[str, str | int | float | bool] | None = None,
    mode: Literal["REUSE"] = "REUSE",
):
    """Instantiate REUSE or request versioned ADAPT from a validated artifact.

    REUSE binds only instance values. ADAPT is for a generalized capability change,
    not ordinary labels/numbers; the application owns immutable version lineage.
    """
    context.context.record_tool("instantiate_reusable_visual")
    candidate = context.context.reusable_visuals.get(version_id)
    if candidate is None:
        raise ValueError("Reusable visual version is not available in this bounded run.")
    if candidate.get("runtime_kind") != "custom-visual":
        raise ValueError("This minimal reusable path currently admits only custom visual packages.")
    build_id = candidate.get("implementation_build_id")
    manifest_digest = candidate.get("manifest_digest")
    canonical_manifest = candidate.get("manifest_contract")
    if not isinstance(build_id, str) or not isinstance(manifest_digest, str) or not isinstance(canonical_manifest, dict):
        raise ValueError("Reusable visual has no authorized canonical implementation.")
    schema = candidate.get("parameter_schema")
    if not isinstance(schema, dict):
        raise ValueError("Reusable visual parameters are invalid.")
    parameters = parameters or {}
    properties = schema.get("properties", {})
    if not isinstance(properties, dict) or not set(parameters) <= set(properties):
        raise ValueError("Reusable visual parameters are outside the approved schema.")
    block = create_reused_custom_visual(
        block_id=block_id,
        meaning=meaning,
        label=label,
        artifact_instance_id=artifact_instance_id,
        bridge_nonce=bridge_nonce,
        build_id=build_id,
        manifest_digest=manifest_digest,
        manifest=canonical_manifest,
        parameters=parameters,
    )
    context.context.reusable_selections.append({"version_id": version_id, "mode": mode, "parameters": parameters})
    return _record_block(context, block)


def _composition_tool_enabled(
    context: RunContextWrapper[CanvasAgentRunContext], agent: Agent[CanvasAgentRunContext],
) -> bool:
    """Once CREATE succeeded, the remaining phase is plan finalization only."""
    return (
        context.context.current_custom_candidate_block_id is None
        and not context.context.create_route_attempted
    )


def _custom_visual_tool_enabled(
    context: RunContextWrapper[CanvasAgentRunContext], agent: Agent[CanvasAgentRunContext],
) -> bool:
    return (
        context.context.current_custom_candidate_block_id is None
        and context.context.custom_attempt_count < 2
    )


def _agent_tools():
    return [
        function_tool(_compute_math, name_override="compute_math", is_enabled=_composition_tool_enabled),
        function_tool(_convert_units, name_override="convert_units", is_enabled=_composition_tool_enabled),
        function_tool(_create_math_board, name_override="create_math_board", is_enabled=_composition_tool_enabled),
        function_tool(_create_2d_scene, name_override="create_2d_scene", is_enabled=_composition_tool_enabled),
        function_tool(_create_diagram, name_override="create_diagram", is_enabled=_composition_tool_enabled),
        function_tool(_create_text_interaction, name_override="create_text_interaction", is_enabled=_composition_tool_enabled),
        function_tool(_create_math_input, name_override="create_math_input", is_enabled=_composition_tool_enabled),
        function_tool(
            _create_custom_visual,
            name_override="create_custom_visual",
            strict_mode=False,
            failure_error_function=_custom_visual_tool_error,
            is_enabled=_custom_visual_tool_enabled,
        ),
        function_tool(_search_reusable_visuals, name_override="search_reusable_visuals", is_enabled=_composition_tool_enabled),
        function_tool(_instantiate_reusable_visual, name_override="instantiate_reusable_visual", strict_mode=False, is_enabled=_composition_tool_enabled),
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
        "create_diagram", "create_text_interaction", "create_math_input", "create_custom_visual",
        "search_reusable_visuals", "instantiate_reusable_visual",
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


def build_canvas_agent(*, api_key: str, model: str, base_url: str | None = None, brief: CanvasBriefV1 | None = None, visual_learner_context: VisualLearnerContextV1 | None = None) -> Agent[CanvasAgentRunContext]:
    """Build the isolated composer; callers retain all Studio ownership."""
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return Agent(
        name="Lina Canvas Agent",
        instructions=CANVAS_AGENT_INSTRUCTIONS if brief is None or visual_learner_context is None else CANVAS_AGENT_INSTRUCTIONS + "\n\nRuntime reasoning skills:\n" + assemble_canvas_intelligence(brief, visual_learner_context),
        tools=_agent_tools(),
        model=OpenAIResponsesModel(model=model, openai_client=client),
        output_type=AgenticCanvasPlanV1,
    )


def canvas_agent_input(brief: CanvasBriefV1, visual_learner_context: VisualLearnerContextV1) -> str:
    """Pass only bounded educational and presentation context, never identity or memory."""
    return json.dumps({
        "canvas_brief": brief.model_dump(mode="json"),
        "visual_learner_context": visual_learner_context.model_dump(mode="json"),
    }, ensure_ascii=False)


def _brief_digest(brief: CanvasBriefV1) -> str:
    return sha256(json.dumps(
        brief.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()


def _parameter_schema(parameters: dict[str, str | int | float | bool]) -> dict[str, object]:
    kind = {str: "string", int: "integer", float: "number", bool: "boolean"}
    return {"type": "object", "properties": {
        key: {"type": kind[type(value)]} for key, value in parameters.items()
    }}


def _canonical_custom_manifest(
    *, objective: str, meaning: str, entities: list[CanvasSemanticEntityV1],
    relations: list[CanvasSemanticRelationV1], quantities: list[CanvasSemanticQuantityV1],
    interactions: list[CanvasSemanticInteractionV1], presentation_steps: list[CanvasPresentationStepV1],
    visual_descriptions: list[str], current_state_schema: dict[str, str], brief_digest: str,
) -> CanvasSemanticManifestV1:
    """Bind model-authored semantics into the complete server-owned manifest envelope."""
    # The model names meaningful targets; the canonical envelope supplies a
    # minimal stable entity record for a referenced target it did not otherwise
    # describe. This removes internal Manifest boilerplate without inventing a
    # fact, value, or relationship.
    known = {item.semantic_id for item in entities}
    references = {item.semantic_id for item in [*quantities, *interactions]}
    references |= {value for item in relations for value in (item.source_id, item.target_id)}
    for semantic_id in sorted(references - known):
        entities.append(CanvasSemanticEntityV1(
            semantic_id=semantic_id, kind="interactive-target", label=semantic_id.replace("-", " ").replace("_", " ").title(),
            educational_meaning=f"A semantic target in: {meaning}", visible_description="A named interactive visual target.",
        ))
    return CanvasSemanticManifestV1.model_validate({
        "version": "canvas-semantic-manifest-v1", "brief_digest": brief_digest,
        "objective": objective, "representation_summary": meaning, "entities": entities,
        "relations": relations, "quantities": quantities, "interactions": interactions,
        "presentation_steps": presentation_steps, "visual_descriptions": visual_descriptions,
        "current_state_schema": current_state_schema,
        "provenance": {"brief_digest": brief_digest, "runtime_kind": "custom-visual"},
    })


def _bound_manifest(
    manifest: CanvasSemanticManifestDraftV1 | dict[str, Any],
    brief_digest: str,
) -> CanvasSemanticManifestV1:
    """Bind the admitted brief identity; models never author provenance hashes."""
    if isinstance(manifest, CanvasSemanticManifestDraftV1):
        draft = manifest
    else:
        raw = dict(manifest)
        raw.pop("brief_digest", None)
        provenance = raw.get("provenance")
        if isinstance(provenance, dict):
            raw["provenance"] = {key: value for key, value in provenance.items() if key != "brief_digest"}
        draft = CanvasSemanticManifestDraftV1.model_validate(raw)
    return draft.bind_brief_digest(brief_digest)


def _plan_repair_input(
    *,
    plan: AgenticCanvasPlanV1,
    registry: CanvasBlockRegistry,
    current_custom_candidate_block_id: str,
) -> str:
    """Give one finalization-only repair the minimum safe run-local context."""

    return json.dumps({
        "kind": "canvas-plan-repair-v1",
        "reason": PlanCompositionInconsistencyError.code,
        "instruction": (
            "Finalize one coherent agentic-canvas-plan-v1 now. Reference the current "
            "custom candidate and only the registered block IDs below. Do not call tools, "
            "create code, restart educational reasoning, or add unregistered blocks."
        ),
        "previous_plan": plan.model_dump(mode="json"),
        "current_custom_candidate_block_id": current_custom_candidate_block_id,
        "available_blocks": [_block_summary(block) for block in registry.blocks()],
    }, ensure_ascii=False)


def _sum_usage(*results: object) -> dict[str, int]:
    keys = ("requests", "input_tokens", "cached_input_tokens", "output_tokens", "total_tokens")
    return {key: sum(_bounded_usage(result)[key] for result in results) for key in keys}


async def compose_canvas_scene_with_trace(*, brief: CanvasBriefV1, visual_learner_context: VisualLearnerContextV1, api_key: str, model: str, base_url: str | None = None, sdk_trace_id: str | None = None, reusable_visuals: dict[str, dict[str, object]] | None = None) -> AgenticCanvasCompositionResult:
    """Run one bounded composition and return only accepted tool-call metadata."""
    context = CanvasAgentRunContext(
        registry=CanvasBlockRegistry(),
        brief_digest=_brief_digest(brief),
        brief_objective=brief.objective,
        reusable_visuals=dict(reusable_visuals or {}),
    )
    trace_id = sdk_trace_id or gen_trace_id()
    agent = build_canvas_agent(api_key=api_key, model=model, base_url=base_url, brief=brief, visual_learner_context=visual_learner_context)
    initial_result = await Runner.run(
        agent,
        input=canvas_agent_input(brief, visual_learner_context),
        context=context,
        hooks=CanvasCompositionRunHooks(),
        # CREATE can require one registry inspection plus a bounded visual package
        # and its final typed plan. Keep the limit finite, but do not cut off an
        # otherwise valid adequacy decision before it can settle.
        max_turns=16,
        run_config=RunConfig(
            workflow_name="lina-agentic-canvas-compose",
            trace_id=trace_id,
            trace_include_sensitive_data=False,
        ),
    )
    plan = AgenticCanvasPlanV1.model_validate(initial_result.final_output)
    if context.create_route_attempted and context.current_custom_candidate_block_id is None:
        _record_final_plan_validation(context, CustomVisualCandidateMissingError.code)
        raise CustomVisualCandidateMissingError(
            tool_failures=context.tool_failures,
            model_turns=context.model_turns,
        )
    result = initial_result
    plan_repaired = False
    try:
        scene = context.registry.materialize_plan(
            plan,
            current_custom_candidate_block_id=context.current_custom_candidate_block_id,
        )
        _record_final_plan_validation(context, "ACCEPTED")
    except PlanCompositionInconsistencyError:
        _record_final_plan_validation(
            context,
            "PLAN_COMPOSITION_INCONSISTENT",
            repair_reason=PlanCompositionInconsistencyError.code,
        )
        # The original Agent is reused with tools removed, so the only possible
        # next action is one bounded, schema-validated plan finalization.
        repair_agent = agent.clone(
            tools=[],
            instructions=agent.instructions + "\n\nYou are in one final-plan coherence repair. Return only the corrected plan.",
        )
        repair_result = await Runner.run(
            repair_agent,
            input=_plan_repair_input(
                plan=plan,
                registry=context.registry,
                current_custom_candidate_block_id=context.current_custom_candidate_block_id or "",
            ),
            context=context,
            hooks=CanvasCompositionRunHooks(),
            max_turns=1,
            run_config=RunConfig(
                workflow_name="lina-agentic-canvas-plan-repair",
                trace_id=trace_id,
                trace_include_sensitive_data=False,
            ),
        )
        plan = AgenticCanvasPlanV1.model_validate(repair_result.final_output)
        scene = context.registry.materialize_plan(
            plan,
            current_custom_candidate_block_id=context.current_custom_candidate_block_id,
        )
        _record_final_plan_validation(context, "REPAIRED_ACCEPTED")
        result = repair_result
        plan_repaired = True
        all_results = (initial_result, repair_result)
    else:
        all_results = (initial_result,)
    generated_images = tuple(image for candidate in all_results for image in _extract_hosted_generated_images(candidate))
    tool_calls = tuple(call for candidate in all_results for call in _extract_tool_call_trace(candidate))
    selected_tools = tuple(dict.fromkeys(call.name for call in tool_calls))
    return AgenticCanvasCompositionResult(
        scene=scene,
        selected_tools=selected_tools,
        tool_call_count=len(tool_calls),
        generated_images=generated_images,
        sdk_trace_id=trace_id,
        model=model,
        usage=_sum_usage(*all_results),
        tool_calls=tool_calls,
        reusable_selections=tuple(context.reusable_selections),
        tool_failures=tuple(context.tool_failures),
        registered_block_ids=tuple(block.block_id for block in context.registry.blocks()),
        plan_block_ids=tuple(placement.block_id for placement in plan.placements),
        current_custom_candidate_block_id=context.current_custom_candidate_block_id,
        plan_repaired=plan_repaired,
        model_turns=tuple(context.model_turns),
    )


async def compose_canvas_scene(*, brief: CanvasBriefV1, visual_learner_context: VisualLearnerContextV1, api_key: str, model: str, base_url: str | None = None, reusable_visuals: dict[str, dict[str, object]] | None = None) -> AgenticCanvasScene:
    """Backward-compatible Scene-only boundary for non-worker callers."""
    composition = await compose_canvas_scene_with_trace(brief=brief, visual_learner_context=visual_learner_context, api_key=api_key, model=model, base_url=base_url, reusable_visuals=reusable_visuals)
    if composition.generated_images:
        raise HostedImageOutputError("Hosted images require the owned Studio asset adoption boundary.")
    return composition.scene
