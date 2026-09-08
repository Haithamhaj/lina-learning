"""Semantic Process context contracts; no renderer pixels or model inference."""

from dataclasses import replace
from uuid import uuid4
import json
import pytest
from services.studio.subjects import (
    production_subject_registry,
    PRODUCTION_CURRENT_PROFILE_VERSIONS,
)
from services.studio.subjects import process_visual as v
from services.studio.tutor_context import (
    StudioTutorWorkspaceContext,
    StudioTutorSceneCapability,
)
from services.tutor.capacity import (
    apply_context_capacity_guardrail,
    serialized_model_request_characters,
)
from services.tutor.context import TutorContext, TutorContextDebug
from services.tutor.runtime import build_tutor_model_payload


def seed():
    return {
        "title": "A butterfly’s life cycle",
        "subtitle": "Four life stages. The return begins a new generation, not the same butterfly becoming an egg.",
        "locale": "en",
        "topology": "cycle",
        "sourceLabel": "Florida Museum of Natural History · Butterfly Life Cycle. Schematic illustrations, not a species identification guide.",
        "sourceUrl": "https://www.floridamuseum.ufl.edu/educators/resource/butterfly-life-cycle/",
        "stages": [
            {"id": i, "label": label, "detail": d, "art": a}
            for i, label, d, a in [
                ("egg", "Egg", "A female lays eggs on a suitable plant.", "egg"),
                (
                    "larva",
                    "Caterpillar",
                    "The larva hatches, feeds and grows.",
                    "larva",
                ),
                (
                    "pupa",
                    "Chrysalis",
                    "The butterfly develops inside the pupa.",
                    "pupa",
                ),
                (
                    "adult",
                    "Adult butterfly",
                    "The adult emerges. After mating, a female can lay eggs.",
                    "butterfly",
                ),
            ]
        ],
        "relations": [
            {"id": f + "-to-" + t, "from": f, "to": t, "label": label}
            for f, t, label in [
                ("egg", "larva", "Hatches into"),
                ("larva", "pupa", "Develops into"),
                ("pupa", "adult", "Adult emerges"),
                ("adult", "egg", "Female lays eggs · new generation"),
            ]
        ],
    }


def workspace():
    scene_id = uuid4()
    state = {
        "scene_status": "ACTIVE",
        "scene_seed": seed(),
        v.ACTIVITY_KEY: v.focus_state(seed(), {}, "pupa"),
    }
    return StudioTutorWorkspaceContext(
        runtime_id=uuid4(),
        snapshot_schema_version="studio-snapshot-v1",
        through_sequence=3,
        snapshot_sequence=3,
        current_scene_id=scene_id,
        current_scene_version=3,
        active_subject_key="SCIENCE",
        active_activity_key=v.ACTIVITY_KEY,
        state_payload=state,
        unseen_events=(),
        observation_id=None,
        current_scene_capability=StudioTutorSceneCapability(
            scene_id,
            "SCIENCE",
            v.PROFILE_VERSION,
            v.ACTIVITY_KEY,
            v.ACTIVITY_VERSION,
            v.RENDERER_KEY,
            v.RENDERER_VERSION,
            ("REQUEST_EXPLANATION",),
            (),
        ),
        visual_scene=v.project_visual(seed(), state[v.ACTIVITY_KEY]),
    )


def test_exact_registration_not_automatic_routing():
    p = production_subject_registry().resolve_profile("SCIENCE", v.PROFILE_VERSION)
    assert p.renderers[0].implementation_status == "AWARENESS_ONLY"
    assert PRODUCTION_CURRENT_PROFILE_VERSIONS["SCIENCE"] != v.PROFILE_VERSION
    v.validate_seed(seed())


def test_projection_is_semantic_bounded_and_stateful():
    w = workspace()
    p = w.as_model_payload()["snapshot"]["visual_scene"]
    assert p["pattern"] == "process_cycle"
    assert p["state"]["focused_stage_id"] == "pupa"
    assert p["state"]["highlighted_relation_ids"] == ["pupa-to-adult"]
    assert (
        p["relations"][-1]["to"] == "egg"
        and "new generation" in p["relations"][-1]["meaning"]
    )
    encoded = json.dumps(w.as_model_payload(), ensure_ascii=False)
    for forbidden in [
        "scene_seed",
        "sourceUrl",
        "sourceLabel",
        '"art"',
        "<svg",
        "css",
        "path",
    ]:
        assert forbidden not in encoded
    assert (
        len(json.dumps(p, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        <= v.MAX_VISUAL_CHARACTERS
    )
    assert (
        "visual_scene"
        not in replace(w, visual_scene=None).as_model_payload()["snapshot"]
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s.update(svg="<svg/>"),
        lambda s: s["relations"][0].update(to="unknown"),
        lambda s: s["stages"][0].update(label="x" * 81),
        lambda s: s.update(locale="xx"),
        lambda s: s["relations"][0].update(id=s["relations"][1]["id"]),
    ],
)
def test_invalid_seed_rejected(mutation):
    s = seed()
    mutation(s)
    with pytest.raises(ValueError):
        v.validate_seed(s)


def test_capacity_drops_whole_optional_units_without_current_question():
    w = workspace()
    ctx = TutorContext(
        question="Why does the chrysalis come after the caterpillar?",
        subject="SCIENCE",
        grade_level=5,
        focus=None,
        session_messages=(),
        retrieval=(),
        intelligence=(),
        debug=TutorContextDebug(None, (), (), (), ()),
        studio_workspace=w,
    )

    def build(c):
        return build_tutor_model_payload(
            question=c.question, studio_context=c.studio_workspace
        )

    full = serialized_model_request_characters(build(ctx))
    result = apply_context_capacity_guardrail(
        ctx, capacity_limit=full - 100, payload_builder=build
    )
    assert result.context.question == ctx.question
    assert result.lineage.dropped_context
    p = result.context.studio_workspace.visual_scene
    assert p["state"]["focused_stage_id"] == "pupa"
    ids = {o["id"] for o in p["objects"]}
    assert all(x["from"] in ids and x["to"] in ids for x in p["relations"])
    assert "scene_seed" not in result.payload["input"]


def test_guidance_is_loaded_only_for_primary_tutor():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    skill = (root / "skills/lina-educational-visuals/SKILL.md").read_text()
    assert "development-only" in skill
    for f in [
        "runtime/tutor/visual-guidance-v1.md",
        "runtime/canvas-specialist/visual-capability-pack-v1.md",
    ]:
        assert "LINA_EDUCATIONAL_VISUALS_GUIDE.md" in (root / f).read_text()
    payload = build_tutor_model_payload(question="hello")
    assert "VISUAL_GUIDANCE_V1" in payload["instructions"]
    assert "SPECIALIST_DISABLED" not in payload["instructions"]


def test_awareness_renderer_cannot_be_routed_as_live_host():
    from services.studio.router import _renderer_matches_need
    from services.studio.workspace_intent import WorkspaceIntent

    intent = WorkspaceIntent.model_validate(
        {
            "version": "workspace-intent-v1",
            "action": "OPEN_ACTIVITY",
            "subject_key": "SCIENCE",
            "concept_keys": [],
            "learning_goal": "Explain process",
            "activity_hint": v.ACTIVITY_KEY,
            "representation_need": "INTERACTIVE",
            "expected_student_response_mode": "WORKSPACE",
            "presentation_sequence": "PARALLEL",
            "source_references": [],
        }
    )
    assert not _renderer_matches_need(v.make_profile().renderers[0], intent)


def test_max_scene_capacity_retains_whole_labels_and_declared_relations():
    s = seed()
    s["stages"] = [
        {"id": f"s{i}", "label": "ع" * 80, "detail": "د" * 300, "art": "egg"}
        for i in range(8)
    ]
    s["relations"] = [
        {"id": f"r{i}", "from": f"s{i}", "to": f"s{(i + 1) % 8}", "label": "ر" * 120}
        for i in range(8)
    ]
    p = v.project_visual(s, v.focus_state(s, {}, "s3"))
    assert v.visual_size(p) <= 4000
    assert next(o for o in p["objects"] if o["id"] == "s3")["detail"] == "د" * 300
    assert all(o["label"] == "ع" * 80 for o in p["objects"])
    assert all(r["meaning"] == "ر" * 120 for r in p["relations"])


def test_unseen_process_event_semantics_do_not_leak_seed():
    from services.studio.tutor_context import StudioTutorEventContext

    w = workspace()
    event = StudioTutorEventContext(
        3,
        "STUDENT",
        "visual.process.focus_object",
        "FOCUS_OBJECT",
        "SCIENCE",
        v.ACTIVITY_KEY,
        2,
        3,
        v.ACTION_VERSION,
        {"action": {"target_id": "pupa"}, "validation": None},
    )
    p = replace(w, unseen_events=(event,)).as_model_payload()
    assert p["unseen_events"][0]["payload"]["action"] == {"target_id": "pupa"}


def test_reveal_is_separate_from_focus_in_server_state():
    from types import SimpleNamespace

    state = v.focus_state(seed(), {}, "larva")
    updated = v.reduce_process(
        {"state_payload": {"scene_seed": seed(), v.ACTIVITY_KEY: state}},
        SimpleNamespace(
            payload={"target_id": "pupa"},
            action_key="REVEAL_OBJECT_DETAIL",
            sequence=4,
            actor="STUDENT",
            id=uuid4(),
        ),
    )
    current = updated["state_payload"][v.ACTIVITY_KEY]
    assert current["focused_stage_id"] == "larva"
    assert current["active_explanation_stage_id"] == "pupa"


def test_aud02_historical_v1_state_is_exact_after_focus_reveal_and_trace():
    from types import SimpleNamespace

    snapshot = {"state_payload": {"scene_seed": seed(), v.ACTIVITY_KEY: {}}}
    for sequence, action, target in ((1, "FOCUS_OBJECT", "larva"), (2, "REVEAL_OBJECT_DETAIL", "pupa"), (3, "TRACE_RELATION", "pupa-to-adult")):
        snapshot = v.reduce_process(snapshot, SimpleNamespace(payload={"target_id": target}, action_key=action, sequence=sequence, actor="STUDENT", id=uuid4()))
    state = snapshot["state_payload"][v.ACTIVITY_KEY]
    assert set(state) == {"selected_stage_id", "focused_stage_id", "active_explanation_stage_id", "revealed_stage_ids", "highlighted_relation_ids"}
    assert state["highlighted_relation_ids"] == ["pupa-to-adult"]


def test_current_visual_is_sanitized_independently_of_interaction_source_activity():
    from services.studio.interactions import StudioInteractionTutorContext

    w = workspace()
    context = StudioInteractionTutorContext(
        uuid4(),
        w.runtime_id,
        uuid4(),
        {
            "event": {
                "activity_key": "process_sequence_workspace",
                "action_payload": {"stage_ids": ["old"]},
            }
        },
        {"active_activity_key": v.ACTIVITY_KEY, "state": dict(w.state_payload)},
    )
    payload = context.as_model_payload()
    assert payload["workspace"]["state"] == {}
    assert payload["source"]["event"]["action_payload"] == {"stage_ids": ["old"]}
    assert "scene_seed" not in json.dumps(payload)


def test_process_accessibility_describes_actual_actions():
    contract = v.make_profile().activities[0].accessibility
    assert "focus" in contract.keyboard_policy.lower()
    assert "reorder" not in contract.keyboard_policy.lower()


@pytest.mark.parametrize("field,value", [("art", {}), ("label", []), ("id", [])])
def test_malformed_object_types_raise_bounded_validation_error(field, value):
    bad = seed()
    bad["stages"][0][field] = value
    with pytest.raises(ValueError):
        v.validate_seed(bad)


def test_cross_activity_current_process_gets_final_capacity_guard(monkeypatch):
    from types import SimpleNamespace
    from services.studio import interactions
    from services.studio.interactions import (
        StudioInteractionTutorContext,
        StudioInteractionTutorService,
    )

    w = workspace()
    source = {
        "event": {
            "activity_key": "process_sequence_workspace",
            "action_payload": {"stage_ids": ["old"]},
        }
    }
    context = StudioInteractionTutorContext(
        uuid4(),
        w.runtime_id,
        uuid4(),
        source,
        {"active_activity_key": v.ACTIVITY_KEY, "state": dict(w.state_payload)},
    )
    svc = StudioInteractionTutorService(bind=None, gateway_factory=lambda _: None)
    settings = SimpleNamespace(
        tutor_context_capacity=64000, tutor_max_output_tokens=1000
    )
    monkeypatch.setattr(interactions, "get_settings", lambda: settings)
    full = svc._model_payload(context, workspace_context=w)
    settings.tutor_context_capacity = serialized_model_request_characters(full) - 100
    bounded = svc._model_payload(context, workspace_context=w)
    assert (
        serialized_model_request_characters(bounded) <= settings.tutor_context_capacity
    )
    assert bounded["studio_interaction_context"]["source"] == source
    assert "scene_seed" not in bounded["input"]
    assert (
        bounded["studio_workspace_context"]["snapshot"]["visual_scene"]["state"][
            "focused_stage_id"
        ]
        == "pupa"
    )
