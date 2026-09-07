import pytest

from services.studio.canvas_specialist import (
    CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION,
    CanvasSpecialistProcessProposal,
    validate_proposal_against_frozen_pack,
)


def test_process_proposal_requires_bounded_supported_semantics() -> None:
    proposal = CanvasSpecialistProcessProposal.model_validate(
        {
            "version": CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION,
            "pattern": "PROCESS",
            "topology": "SEQUENCE",
            "title": "Butterfly life cycle",
            "stages": [
                {"semantic_key": "egg", "label": "Egg", "support_ids": ["F1"]},
                {"semantic_key": "larva", "label": "Larva", "support_ids": ["F2"]},
            ],
            "relations": [
                {"relation_key": "growth", "source_semantic_key": "egg", "target_semantic_key": "larva", "support_ids": ["R1"]}
            ],
            "text_equivalent": "Egg becomes larva.",
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
                "stages": [
                    {"semantic_key": "one", "label": "One", "support_ids": ["F1"], "svg": "<svg/>"},
                    {"semantic_key": "two", "label": "Two", "support_ids": ["F2"]},
                ],
                "relations": [],
                "text_equivalent": "Unsafe",
            }
        )


def test_proposal_cannot_claim_support_or_affordances_absent_from_frozen_pack() -> None:
    proposal = CanvasSpecialistProcessProposal.model_validate({
        "version": CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION, "pattern": "PROCESS", "topology": "SEQUENCE", "title": "Steps",
        "stages": [{"semantic_key": "one", "label": "One", "support_ids": ["F1"]}, {"semantic_key": "two", "label": "Two", "support_ids": ["F9"]}],
        "relations": [], "text_equivalent": "One then two.", "interaction_affordances": ["UNAUTHORIZED"],
    })
    with pytest.raises(ValueError, match="frozen"):
        validate_proposal_against_frozen_pack(proposal, {
            "pattern": "PROCESS", "topology": "SEQUENCE",
            "semantic_alignment": {"required_semantics": [{"id": "F1"}], "required_relations": []},
            "allowed_affordances": ["FOCUS_OBJECT"], "capability_pack": {"process_stage_limit": [2, 8]},
        })
