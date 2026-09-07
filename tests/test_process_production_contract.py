"""CS-05 production Process contract regressions."""

from services.studio.subjects.process_production import (
    ACTIVITY_KEY,
    PROFILE_VERSION,
    RENDERER_KEY,
    proposal_to_scene_seed,
)
from services.studio.process_production_acceptance import ProcessAcceptanceFailure
from services.studio.interactions import _visual_interaction_source
from services.studio.canvas_specialist import (
    CanvasSpecialistProcessProposal,
    validate_proposal_against_frozen_pack,
)
from types import SimpleNamespace
import pytest


def test_replacement_failure_is_a_distinct_atomic_acceptance_failure():
    """The durable PostgreSQL matrix injects this boundary before its outer commit."""
    assert str(ProcessAcceptanceFailure("INJECTED_REPLACEMENT_FAILURE")) == "INJECTED_REPLACEMENT_FAILURE"


def test_production_process_identity_is_additive_and_adapts_a_supported_sequence():
    proposal = {
        "version": "canvas-specialist-process-proposal-v1",
        "pattern": "PROCESS",
        "topology": "SEQUENCE",
        "title": "Water filtration",
        "subtitle": "Water moves through each cleaning step.",
        "stages": [
            {"semantic_key": "collect", "label": "Collect", "detail": "Collect water.", "support_ids": ["stage-collect"], "art_handle": "drop"},
            {"semantic_key": "filter", "label": "Filter", "detail": "Filter particles.", "support_ids": ["stage-filter"], "art_handle": "filter"},
        ],
        "relations": [
            {"relation_key": "collect-to-filter", "source_semantic_key": "collect", "target_semantic_key": "filter", "label": "then", "support_ids": ["relation-collect-filter"]},
        ],
        "text_equivalent": "Collect water, then filter it.",
        "focus_intent": None,
        "motion_intents": [],
        "interaction_affordances": ["FOCUS_OBJECT", "REVEAL_OBJECT_DETAIL", "TRACE_RELATION"],
    }
    pack = {
        "pattern": "PROCESS",
        "topology": "SEQUENCE",
        "capability_pack": {"process_stage_limit": [2, 8]},
        "semantic_alignment": {
            "required_semantics": [{"id": "stage-collect"}, {"id": "stage-filter"}],
            "required_relations": [{"id": "relation-collect-filter"}],
        },
        "allowed_affordances": ["FOCUS_OBJECT", "REVEAL_OBJECT_DETAIL", "TRACE_RELATION"],
        "allowed_art_handles": ["drop", "filter"],
    }

    seed = proposal_to_scene_seed(proposal, pack, locale="en", direction="ltr")

    assert PROFILE_VERSION == "process-visual-production-profile-v1"
    assert ACTIVITY_KEY == "process_visual_production"
    assert RENDERER_KEY == "process-visual-production"
    assert seed["topology"] == "sequence"
    assert seed["stages"][0]["art"] == "drop"
    assert seed["relations"] == [{"id": "collect-to-filter", "from": "collect", "to": "filter", "label": "then"}]


def test_production_relation_explanation_keeps_exact_relation_provenance():
    source = _visual_interaction_source(
        SimpleNamespace(activity_key=ACTIVITY_KEY),
        {"target_id": "collect-to-filter"},
        {"scene_seed": {
            "title": "Water filtration", "subtitle": "Water moves through each step.", "locale": "en", "topology": "sequence",
            "sourceLabel": "Tutor-approved Process explanation", "sourceUrl": "https://lina.local/process",
            "stages": [
                {"id": "collect", "label": "Collect", "detail": "Collect water.", "art": "drop"},
                {"id": "filter", "label": "Filter", "detail": "Filter particles.", "art": "filter"},
            ],
            "relations": [{"id": "collect-to-filter", "from": "collect", "to": "filter", "label": "then"}],
        }},
    )

    assert source["current_interaction"] == {
        "action": "REQUEST_EXPLANATION", "target_id": "collect-to-filter", "target_kind": "relation",
        "from": "collect", "to": "filter", "meaning": "then",
    }


def test_semantic_support_keeps_stage_and_relation_provenance_separate_and_respects_must_not_imply():
    proposal = CanvasSpecialistProcessProposal.model_validate({
        "version": "canvas-specialist-process-proposal-v1", "pattern": "PROCESS", "topology": "SEQUENCE",
        "title": "Water filtration", "subtitle": None, "text_equivalent": "Collect water, then filter it.",
        "stages": [
            {"semantic_key": "collect", "label": "Collect", "detail": None, "support_ids": ["stage-collect"], "art_handle": "drop"},
            {"semantic_key": "filter", "label": "Filter", "detail": None, "support_ids": ["stage-filter"], "art_handle": "filter"},
        ],
        "relations": [{"relation_key": "collect-to-filter", "source_semantic_key": "collect", "target_semantic_key": "filter", "label": "then", "support_ids": ["relation-collect-filter"]}],
        "focus_intent": None, "motion_intents": [], "interaction_affordances": ["FOCUS_OBJECT"],
    })
    pack = {
        "pattern": "PROCESS", "topology": "SEQUENCE", "capability_pack": {"process_stage_limit": [2, 8]},
        "semantic_alignment": {"required_semantics": [{"id": "stage-collect"}, {"id": "stage-filter"}], "required_relations": [{"id": "relation-collect-filter"}], "must_not_imply": ["collect water twice"]},
        "allowed_affordances": ["FOCUS_OBJECT"], "allowed_art_handles": ["drop", "filter"],
    }

    validate_proposal_against_frozen_pack(proposal, pack)
    swapped = proposal.model_copy(update={"relations": [proposal.relations[0].model_copy(update={"support_ids": ["stage-collect"]})]})
    with pytest.raises(ValueError, match="semantic alignment"):
        validate_proposal_against_frozen_pack(swapped, pack)
    forbidden = proposal.model_copy(update={"title": "Collect water twice"})
    with pytest.raises(ValueError, match="forbidden frozen meaning"):
        validate_proposal_against_frozen_pack(forbidden, pack)
