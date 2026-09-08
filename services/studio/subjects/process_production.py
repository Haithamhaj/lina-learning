"""CS-05 production Process contract, isolated from the historical awareness profile."""

from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping

from services.studio.canvas_specialist import proposal_contract, validate_proposal_against_frozen_pack
from services.studio.subjects import process_visual as awareness
from services.studio.subjects.contracts import (
    ActivityActionContract, ActivityContract, InteractionPolicy, PayloadValidatorContract,
    ReducerContract, RendererContract, SemanticValidationPolicy,
)
from services.studio.subjects.process_sequence import make_process_sequence_profile

PROFILE_VERSION = "process-visual-production-profile-v1"
ACTIVITY_KEY = "process_visual_production"
ACTIVITY_VERSION = "process-visual-production-activity-v1"
RENDERER_KEY = "process-visual-production"
RENDERER_VERSION = "process-visual-production-renderer-v1"
SEED_VERSION = "process-visual-production-seed-v1"
ACTION_VERSION = "process-visual-production-action-v1"
EVENT_VERSION = "process-visual-production-event-v1"
SCENE_PAYLOAD_SCHEMA_VERSION = SEED_VERSION


def proposal_to_scene_seed(proposal_payload: Mapping[str, object], pack: Mapping[str, object], *, locale: str, direction: str) -> dict[str, object]:
    """Map only an already durable, frozen-supported proposal to safe renderer data."""
    if locale not in ("en", "ar") or direction not in ("ltr", "rtl", "auto"):
        raise ValueError("Unsupported production Process locale/direction.")
    capability = pack.get("capability_pack")
    if not isinstance(capability, Mapping):
        raise ValueError("Missing Process capability identity.")
    identity = capability.get("identity") or "process-capability-pack-v1"
    proposal = proposal_contract(str(identity), str(proposal_payload.get("version"))).model_validate(proposal_payload)
    validate_proposal_against_frozen_pack(proposal, dict(pack))
    topology = proposal.topology.lower()
    fallback_art = "idea"
    seed = {
        "title": proposal.title,
        "subtitle": proposal.subtitle or proposal.text_equivalent,
        "locale": locale,
        "topology": topology,
        "sourceLabel": "Tutor-approved Process explanation",
        "sourceUrl": "https://lina.local/process",
        "stages": [
            {"id": item.semantic_key, "label": item.label, "detail": item.detail or item.label,
             "art": item.art_handle or fallback_art}
            for item in proposal.stages
        ],
        "relations": [
            {"id": item.relation_key, "from": item.source_semantic_key,
             "to": item.target_semantic_key, "label": item.label or "then"}
            for item in proposal.relations
        ],
        "motion_intents": list(proposal.motion_intents),
    }
    validate_seed(seed)
    return seed


def validate_seed(seed: Mapping[str, object]) -> None:
    historical = dict(seed)
    motion = historical.pop("motion_intents", [])
    topology = historical.get("topology")
    permitted = {"REVEAL_IN_ORDER", "TRACE_SEQUENCE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"} if topology == "sequence" else {"REVEAL_IN_ORDER", "TRACE_CYCLE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"}
    if not isinstance(motion, list) or any(not isinstance(value, str) or value not in permitted for value in motion) or len(set(motion)) != len(motion):
        raise ValueError("Invalid Process motion intents.")
    awareness.validate_seed(historical)


def validate_action(payload: Mapping[str, object]) -> None:
    awareness.validate_action(payload)


def view_state(seed: Mapping[str, object], state: Mapping[str, object]) -> dict[str, object]:
    """Production-only additive Process state; historical V1 remains unchanged."""
    ids = {stage["id"] for stage in seed["stages"]}
    relations = {relation["id"] for relation in seed["relations"]}
    result = {"selected_stage_id": None, "focused_stage_id": None, "active_explanation_stage_id": None,
              "revealed_stage_ids": [], "highlighted_relation_ids": [], "tracing_relation_id": None}
    if not isinstance(state, Mapping) or set(state) - set(result):
        raise ValueError("Unknown production Process state.")
    result.update(deepcopy(state))
    for key in ("selected_stage_id", "focused_stage_id", "active_explanation_stage_id"):
        if result[key] is not None and (not isinstance(result[key], str) or result[key] not in ids):
            raise ValueError("Unknown selected stage.")
    if result["tracing_relation_id"] is not None and (not isinstance(result["tracing_relation_id"], str) or result["tracing_relation_id"] not in relations):
        raise ValueError("Unknown tracing relation.")
    for key, allowed in (("revealed_stage_ids", ids), ("highlighted_relation_ids", relations)):
        values = result[key]
        if not isinstance(values, list) or len(values) > len(allowed) or any(not isinstance(value, str) or value not in allowed for value in values) or len(set(values)) != len(values):
            raise ValueError("Unknown state identities.")
    return result


def focus_state(seed: Mapping[str, object], state: Mapping[str, object], target: str) -> dict[str, object]:
    result = view_state(seed, state)
    if target not in {stage["id"] for stage in seed["stages"]}:
        raise ValueError("Unknown focus target.")
    result.update(selected_stage_id=target, focused_stage_id=target, active_explanation_stage_id=target,
                  highlighted_relation_ids=[relation["id"] for relation in seed["relations"] if relation["from"] == target],
                  tracing_relation_id=None)
    if target not in result["revealed_stage_ids"]:
        result["revealed_stage_ids"].append(target)
    return result


def reduce_process(snapshot: dict[str, object], event: object) -> dict[str, object]:
    result = deepcopy(snapshot)
    state = result["state_payload"]
    seed = state["scene_seed"]
    validate_seed(seed)
    current = view_state(seed, state.get(ACTIVITY_KEY, {}))
    validate_action(event.payload)
    target = event.payload["target_id"]
    stage_ids = {stage["id"] for stage in seed["stages"]}
    relation_ids = {relation["id"] for relation in seed["relations"]}
    if event.action_key in ("FOCUS_OBJECT", "REVEAL_OBJECT_DETAIL"):
        if target not in stage_ids:
            raise ValueError("Unknown stage target.")
        if event.action_key == "FOCUS_OBJECT":
            current = focus_state(seed, current, target)
        else:
            current["active_explanation_stage_id"] = target
            if target not in current["revealed_stage_ids"]:
                current["revealed_stage_ids"].append(target)
    elif event.action_key == "TRACE_RELATION":
        if target not in relation_ids:
            raise ValueError("Unknown relation target.")
        current["highlighted_relation_ids"] = [target]
        current["tracing_relation_id"] = target
    elif event.action_key == "REQUEST_EXPLANATION":
        if target not in stage_ids | relation_ids:
            raise ValueError("Unknown explanation target.")
    else:
        raise ValueError("Unsupported Process action.")
    state[ACTIVITY_KEY] = current
    result["latest_event_sequence"] = event.sequence
    if event.actor == "STUDENT":
        result["last_meaningful_student_event_id"] = event.id
    return result


def project_visual(seed: Mapping[str, object], state: Mapping[str, object]) -> dict[str, object]:
    normalized = view_state(seed, state)
    normalized.pop("tracing_relation_id")
    projected = awareness.project_visual({key: value for key, value in seed.items() if key != "motion_intents"}, normalized)
    projected["motion_intents"] = list(seed.get("motion_intents", []))
    return projected


def make_profile():
    actions = tuple(ActivityActionContract(
        key, "visual.process.production." + key.lower(), EVENT_VERSION, ACTION_VERSION,
        "process-visual-production-target",
        InteractionPolicy.TUTOR_TRIGGERING if key == "REQUEST_EXPLANATION" else InteractionPolicy.RECORD_ONLY,
        SemanticValidationPolicy.NONE,
        interaction_kind="PROCESS_VISUAL_EXPLANATION" if key == "REQUEST_EXPLANATION" else None,
    ) for key in awareness.ACTIONS)
    activity = ActivityContract(ACTIVITY_KEY, ACTIVITY_VERSION, "SCIENCE", "lina.process", RENDERER_KEY,
        RENDERER_VERSION, SEED_VERSION, "process-visual-production-seed", actions,
        "Explanatory only; no grading or learning completion.", "Semantic focus/detail only.", (),
        "Continue in Chat with semantic text.", awareness.ACCESSIBILITY,
        "process-visual-production-reducer", "v1", requires_explicit_hint=True)
    renderer = RendererContract(RENDERER_KEY, RENDERER_VERSION, "SCIENCE", (ACTIVITY_KEY,), SEED_VERSION,
        True, awareness.ACTIONS, (), "process-visual-production-state-v1", awareness.ACCESSIBILITY,
        False, False, True, "PRODUCTION")
    from dataclasses import replace
    return replace(make_process_sequence_profile(), profile_version=PROFILE_VERSION, concept_namespace="lina.process",
        tutor_guidance_fragment="visual-guidance-v1", activities=(activity,), renderers=(renderer,), validators=(),
        payload_validators=(PayloadValidatorContract("process-visual-production-seed", SEED_VERSION, validate_seed),
                            PayloadValidatorContract("process-visual-production-target", ACTION_VERSION, validate_action)),
        reducers=(ReducerContract("process-visual-production-reducer", "v1", reduce_process),))
