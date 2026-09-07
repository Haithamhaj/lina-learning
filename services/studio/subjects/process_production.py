"""CS-05 production Process contract, isolated from the historical awareness profile."""

from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping

from services.studio.canvas_specialist import CanvasSpecialistProcessProposal, validate_proposal_against_frozen_pack
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
    proposal = CanvasSpecialistProcessProposal.model_validate(proposal_payload)
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
    }
    awareness.validate_seed(seed)
    return seed


def validate_seed(seed: Mapping[str, object]) -> None:
    awareness.validate_seed(seed)


def validate_action(payload: Mapping[str, object]) -> None:
    awareness.validate_action(payload)


def reduce_process(snapshot: dict[str, object], event: object) -> dict[str, object]:
    # The historical reducer keys state by its activity. Preserve its exact semantic rules,
    # then place the result in the additive production activity namespace.
    clone = deepcopy(snapshot)
    state = clone["state_payload"]
    if ACTIVITY_KEY in state:
        state[awareness.ACTIVITY_KEY] = state.pop(ACTIVITY_KEY)
    result = awareness.reduce_process(clone, event)
    state = result["state_payload"]
    if awareness.ACTIVITY_KEY in state:
        state[ACTIVITY_KEY] = state.pop(awareness.ACTIVITY_KEY)
    return result


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
