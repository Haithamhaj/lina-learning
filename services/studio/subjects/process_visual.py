"""Exact awareness-only Process contract; no Router activation or specialist execution."""

from copy import deepcopy
import json
import re
from collections.abc import Mapping
from dataclasses import replace
from services.studio.subjects.contracts import (
    AccessibilityContract,
    ReducedMotionPolicy,
    ActivityActionContract,
    ActivityContract,
    InteractionPolicy,
    PayloadValidatorContract,
    ReducerContract,
    RendererContract,
    SemanticValidationPolicy,
)
from services.studio.subjects.process_sequence import (
    make_process_sequence_profile,
)

PROFILE_VERSION = "process-visual-awareness-profile-v1"
ACTIVITY_KEY = "process_visual_context"
ACTIVITY_VERSION = "process-visual-context-v1"
RENDERER_KEY = "process-visual-awareness"
RENDERER_VERSION = "process-visual-awareness-v1"
SEED_VERSION = "process-visual-seed-v1"
ACTION_VERSION = "process-visual-action-v1"
EVENT_VERSION = "process-visual-event-v1"
MAX_VISUAL_CHARACTERS = (
    4000  # Existing Tutor ContextBudget.max_question_characters convention.
)
ACTIONS = (
    "FOCUS_OBJECT",
    "REVEAL_OBJECT_DETAIL",
    "TRACE_RELATION",
    "REQUEST_EXPLANATION",
)
ART = {
    "egg",
    "larva",
    "pupa",
    "butterfly",
    "drop",
    "filter",
    "vessel",
    "idea",
    "draft",
    "review",
}

ACCESSIBILITY = AccessibilityContract(
    accessible_equivalent="Named stages, relations and explanatory text remain available without spatial rendering.",
    keyboard_policy="Keyboard focus, reveal, trace and explanation controls issue the same semantic IDs as pointer actions.",
    touch_policy="Tap selects semantic objects; no drag or hover is required.",
    direction_policy="Arabic and mixed text preserve causal relation direction.",
    mobile_fallback="Deliberate narrow spatial sequence/cycle with readable labels and explicit return.",
    safe_fallback="Text-only Tutor explanation remains available.",
    reduced_motion_policy=ReducedMotionPolicy.OPTIONAL_WITH_STATIC_EQUIVALENT,
)


def _text(value, limit):
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > limit
        or any(ord(c) < 32 for c in value)
        or "<" in value
        or ">" in value
    ):
        raise ValueError("Process text must be bounded plain text.")


def _id(value):
    _text(value, 64)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Invalid semantic ID.")


def validate_seed(seed):
    if not isinstance(seed, Mapping) or set(seed) != {
        "title",
        "subtitle",
        "locale",
        "topology",
        "sourceLabel",
        "sourceUrl",
        "stages",
        "relations",
    }:
        raise ValueError("Unknown Process seed shape.")
    for key, limit in [
        ("title", 160),
        ("subtitle", 300),
        ("sourceLabel", 300),
        ("sourceUrl", 512),
    ]:
        _text(seed[key], limit)
    if seed["locale"] not in ("en", "ar") or seed["topology"] not in (
        "cycle",
        "sequence",
    ):
        raise ValueError("Unsupported Process locale/topology.")
    stages, relations = seed["stages"], seed["relations"]
    if (
        not isinstance(stages, list)
        or not 2 <= len(stages) <= 8
        or not isinstance(relations, list)
    ):
        raise ValueError("Unsupported Process count.")
    for s in stages:
        if not isinstance(s, dict) or set(s) != {"id", "label", "detail", "art"}:
            raise ValueError("Unknown stage shape.")
        _id(s["id"])
        _text(s["label"], 80)
        _text(s["detail"], 300)
        if not isinstance(s["art"], str) or s["art"] not in ART:
            raise ValueError("Unsupported artwork handle.")
    ids = [s["id"] for s in stages]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate stage ID.")
    expected = list(zip(ids, ids[1:])) + (
        [(ids[-1], ids[0])] if seed["topology"] == "cycle" else []
    )
    if len(relations) != len(expected):
        raise ValueError("Relations must declare exact topology.")
    seen = set()
    for relation, (start, end) in zip(relations, expected):
        if not isinstance(relation, dict) or set(relation) != {
            "id",
            "from",
            "to",
            "label",
        }:
            raise ValueError("Unknown relation shape.")
        _id(relation["id"])
        _text(relation["label"], 120)
        if (
            relation["id"] in seen
            or relation["id"] in ids
            or (relation["from"], relation["to"]) != (start, end)
        ):
            raise ValueError("Invalid relation identity/topology.")
        seen.add(relation["id"])


def validate_action(payload):
    if not isinstance(payload, Mapping) or set(payload) != {"target_id"}:
        raise ValueError("Expected semantic target only.")
    _id(payload["target_id"])


def view_state(seed, state):
    ids = {s["id"] for s in seed["stages"]}
    relations = {r["id"] for r in seed["relations"]}
    result = {
        "selected_stage_id": None,
        "focused_stage_id": None,
        "active_explanation_stage_id": None,
        "revealed_stage_ids": [],
        "highlighted_relation_ids": [],
    }
    if not isinstance(state, Mapping) or set(state) - set(result):
        raise ValueError("Unknown Process state.")
    result.update(deepcopy(state))
    for k in ("selected_stage_id", "focused_stage_id", "active_explanation_stage_id"):
        if result[k] is not None and (
            not isinstance(result[k], str) or result[k] not in ids
        ):
            raise ValueError("Unknown selected stage.")
    for k, allowed in [
        ("revealed_stage_ids", ids),
        ("highlighted_relation_ids", relations),
    ]:
        values = result[k]
        if (
            not isinstance(values, list)
            or len(values) > len(allowed)
            or any(not isinstance(x, str) or x not in allowed for x in values)
            or len(set(values)) != len(values)
        ):
            raise ValueError("Unknown state identities.")
    return result


def focus_state(seed, state, target):
    result = view_state(seed, state)
    if target not in {s["id"] for s in seed["stages"]}:
        raise ValueError("Unknown focus target.")
    result.update(
        selected_stage_id=target,
        focused_stage_id=target,
        active_explanation_stage_id=target,
        highlighted_relation_ids=[
            r["id"] for r in seed["relations"] if r["from"] == target
        ],
    )
    if target not in result["revealed_stage_ids"]:
        result["revealed_stage_ids"].append(target)
    return result


def reduce_process(snapshot, event):
    result = deepcopy(snapshot)
    state = result["state_payload"]
    seed = state["scene_seed"]
    validate_seed(seed)
    current = view_state(seed, state.get(ACTIVITY_KEY, {}))
    payload = event.payload
    validate_action(payload)
    target = payload["target_id"]
    stage_ids = {s["id"] for s in seed["stages"]}
    relation_ids = {r["id"] for r in seed["relations"]}
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


def make_profile():
    actions = tuple(
        ActivityActionContract(
            key,
            "visual.process." + key.lower(),
            EVENT_VERSION,
            ACTION_VERSION,
            "process-visual-target",
            InteractionPolicy.TUTOR_TRIGGERING
            if key == "REQUEST_EXPLANATION"
            else InteractionPolicy.RECORD_ONLY,
            SemanticValidationPolicy.NONE,
            interaction_kind="PROCESS_VISUAL_EXPLANATION"
            if key == "REQUEST_EXPLANATION"
            else None,
        )
        for key in ACTIONS
    )
    activity = ActivityContract(
        ACTIVITY_KEY,
        ACTIVITY_VERSION,
        "SCIENCE",
        "lina.process",
        RENDERER_KEY,
        RENDERER_VERSION,
        SEED_VERSION,
        "process-visual-seed",
        actions,
        "Explanatory only; no grading or learning completion.",
        "Semantic focus/detail only.",
        (),
        "Continue in Chat with semantic text.",
        ACCESSIBILITY,
        "process-visual-reducer",
        "v1",
        requires_explicit_hint=True,
    )
    renderer = RendererContract(
        RENDERER_KEY,
        RENDERER_VERSION,
        "SCIENCE",
        (ACTIVITY_KEY,),
        SEED_VERSION,
        True,
        ACTIONS,
        (),
        "process-visual-state-v1",
        ACCESSIBILITY,
        False,
        False,
        True,
        "AWARENESS_ONLY",
    )
    return replace(
        make_process_sequence_profile(),
        profile_version=PROFILE_VERSION,
        concept_namespace="lina.process",
        tutor_guidance_fragment="visual-guidance-v1",
        activities=(activity,),
        renderers=(renderer,),
        validators=(),
        payload_validators=(
            PayloadValidatorContract(
                "process-visual-seed", SEED_VERSION, validate_seed
            ),
            PayloadValidatorContract(
                "process-visual-target", ACTION_VERSION, validate_action
            ),
        ),
        reducers=(ReducerContract("process-visual-reducer", "v1", reduce_process),),
    )


def visual_size(value):
    return len(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def reduce_visual(value):
    """Drop one whole optional unit; preserve focus/selection until the final omission."""
    if value is None:
        return None
    p = deepcopy(value)
    state = p["state"]
    priority = {
        state["focused_stage_id"],
        state["selected_stage_id"],
        state["active_explanation_stage_id"],
    } - {None}
    for obj in reversed(p["objects"]):
        if obj["id"] not in priority and "detail" in obj:
            del obj["detail"]
            return p
    for relation in reversed(p["relations"]):
        if (
            relation["from"] not in priority
            and relation["to"] not in priority
            and relation["id"] not in state["highlighted_relation_ids"]
        ):
            p["relations"].remove(relation)
            return p
    endpoints = {x for rel in p["relations"] for x in (rel["from"], rel["to"])}
    for obj in reversed(p["objects"]):
        if obj["id"] not in priority | endpoints:
            p["objects"].remove(obj)
            state["revealed_stage_ids"] = [
                i for i in state["revealed_stage_ids"] if i != obj["id"]
            ]
            return p
    if "objective" in p:
        del p["objective"]
        return p
    if p["relations"]:
        removed = p["relations"].pop()
        state["highlighted_relation_ids"] = [
            i for i in state["highlighted_relation_ids"] if i != removed["id"]
        ]
        return p
    for obj in p["objects"]:
        if "detail" in obj:
            del obj["detail"]
            return p
    return None


def project_visual(seed, state):
    validate_seed(seed)
    state = view_state(seed, state)
    p = {
        "schema_version": "process-visual-context-v1",
        "pattern": "process_" + seed["topology"],
        "objective": seed["subtitle"],
        "objects": [
            {k: s[k] for k in ("id", "label", "detail")} for s in seed["stages"]
        ],
        "relations": [
            {"id": r["id"], "from": r["from"], "to": r["to"], "meaning": r["label"]}
            for r in seed["relations"]
        ],
        "state": state,
    }
    while p is not None and visual_size(p) > MAX_VISUAL_CHARACTERS:
        p = reduce_visual(p)
    return p
