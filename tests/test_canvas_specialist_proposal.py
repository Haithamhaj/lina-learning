import pytest

from services.studio.canvas_specialist import (
    CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION,
    CanvasSpecialistProcessProposal,
    CanvasSpecialistProcessProposalV2,
    validate_proposal_against_frozen_pack,
)


def test_v2_motion_grammar_is_topology_bound_by_the_frozen_pack():
    proposal = {
        "version": "canvas-specialist-process-proposal-v2", "pattern": "PROCESS", "topology": "SEQUENCE",
        "title": "Water", "subtitle": None,
        "stages": [
            {"semantic_key": "collect", "label": "Collect", "detail": None, "support_ids": ["s1"], "art_handle": "drop"},
            {"semantic_key": "filter", "label": "Filter", "detail": None, "support_ids": ["s2"], "art_handle": "filter"},
        ],
        "relations": [{"relation_key": "then", "source_semantic_key": "collect", "target_semantic_key": "filter", "label": "Then", "support_ids": ["r1"]}],
        "text_equivalent": "Collect then filter.", "focus_intent": None,
        "motion_intents": ["REVEAL_IN_ORDER", "TRACE_SEQUENCE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"],
        "interaction_affordances": ["FOCUS_OBJECT"],
    }
    pack = {"pattern": "PROCESS", "topology": "SEQUENCE", "capability_pack": {"identity": "process-capability-pack-v2", "process_stage_limit": [2, 8]}, "semantic_alignment": {"required_semantics": [{"id": "s1"}, {"id": "s2"}], "required_relations": [{"id": "r1"}], "must_not_imply": []}, "allowed_affordances": ["FOCUS_OBJECT"], "allowed_motion_intents": proposal["motion_intents"], "allowed_art_handles": ["drop", "filter"]}
    validated = CanvasSpecialistProcessProposalV2.model_validate(proposal)
    validate_proposal_against_frozen_pack(validated, pack)
    proposal["motion_intents"] = ["TRACE_CYCLE"]
    with pytest.raises(ValueError, match="motion"):
        validate_proposal_against_frozen_pack(CanvasSpecialistProcessProposalV2.model_validate(proposal), pack)


def test_process_proposal_schema_is_recursively_strict_and_required() -> None:
    """The exact structured-output schema accepts no omitted object fields."""
    schema = CanvasSpecialistProcessProposal.model_json_schema()

    def visit(node: object) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False
            assert set(node.get("properties", {})) == set(node.get("required", []))
        for child in node.values():
            if isinstance(child, list):
                for item in child:
                    visit(item)
            else:
                visit(child)

    visit(schema)


def test_process_proposal_rejects_free_form_focus_implementation_control() -> None:
    with pytest.raises(ValueError):
        CanvasSpecialistProcessProposal.model_validate(
            {
                "version": CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION,
                "pattern": "PROCESS",
                "topology": "SEQUENCE",
                "title": "Steps",
                "subtitle": None,
                "stages": [
                {"semantic_key": "one", "label": "One", "detail": None, "support_ids": ["F1"], "art_handle": None},
                {"semantic_key": "two", "label": "Two", "detail": None, "support_ids": ["F2"], "art_handle": None},
                ],
                "relations": [],
                "text_equivalent": "One then two.",
                "focus_intent": "Use React renderer",
                "motion_intents": [],
                "interaction_affordances": [],
            }
        )


def test_process_proposal_requires_bounded_supported_semantics() -> None:
    proposal = CanvasSpecialistProcessProposal.model_validate(
        {
            "version": CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION,
            "pattern": "PROCESS",
            "topology": "SEQUENCE",
            "title": "Butterfly life cycle",
            "subtitle": None,
            "stages": [
                {"semantic_key": "egg", "label": "Egg", "detail": None, "support_ids": ["F1"], "art_handle": None},
                {"semantic_key": "larva", "label": "Larva", "detail": None, "support_ids": ["F2"], "art_handle": None},
            ],
            "relations": [
                {"relation_key": "growth", "source_semantic_key": "egg", "target_semantic_key": "larva", "label": None, "support_ids": ["R1"]}
            ],
            "text_equivalent": "Egg becomes larva.",
            "focus_intent": None,
            "motion_intents": [],
            "interaction_affordances": [],
        }
    )

    assert proposal.stages[0].semantic_key == "egg"


def test_process_proposal_rejects_executable_or_unknown_fields() -> None:
    with pytest.raises(ValueError):
        CanvasSpecialistProcessProposal.model_validate(
            {
                "version": CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION,
                "pattern": "PROCESS",
                "topology": "SEQUENCE",
                "title": "Unsafe",
                "subtitle": None,
                "stages": [
                    {"semantic_key": "one", "label": "One", "detail": None, "support_ids": ["F1"], "art_handle": None, "svg": "<svg/>"},
                    {"semantic_key": "two", "label": "Two", "detail": None, "support_ids": ["F2"], "art_handle": None},
                ],
                "relations": [],
                "text_equivalent": "Unsafe",
                "focus_intent": None,
                "motion_intents": [],
                "interaction_affordances": [],
            }
        )


def test_proposal_cannot_claim_support_or_affordances_absent_from_frozen_pack() -> None:
    proposal = CanvasSpecialistProcessProposal.model_validate({
        "version": CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION, "pattern": "PROCESS", "topology": "SEQUENCE", "title": "Steps", "subtitle": None,
        "stages": [{"semantic_key": "one", "label": "One", "detail": None, "support_ids": ["F1"], "art_handle": None}, {"semantic_key": "two", "label": "Two", "detail": None, "support_ids": ["F9"], "art_handle": None}],
        "relations": [], "text_equivalent": "One then two.", "focus_intent": None, "motion_intents": [], "interaction_affordances": ["TRACE_RELATION"],
    })
    with pytest.raises(ValueError, match="frozen"):
        validate_proposal_against_frozen_pack(proposal, {
            "pattern": "PROCESS", "topology": "SEQUENCE",
            "semantic_alignment": {"required_semantics": [{"id": "F1"}], "required_relations": []},
            "allowed_affordances": ["FOCUS_OBJECT"], "capability_pack": {"process_stage_limit": [2, 8]},
        })
