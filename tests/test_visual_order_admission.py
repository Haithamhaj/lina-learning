from __future__ import annotations

import pytest

from services.studio.visual_order import (
    VisualOrderAdmissionError,
    admit_visual_order,
)


def _order(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "version": "workspace-visual-order-v1",
        "operation": "COMPOSE",
        "pattern": "PROCESS",
        "topology": "SEQUENCE",
        "objective": "Explain how a caterpillar becomes a butterfly.",
        "required_semantics": ["Egg becomes larva", "Larva becomes pupa", "Adult emerges"],
        "required_relations": ["Egg to larva", "Larva to pupa", "Pupa to adult"],
        "must_not_imply": ["The same adult becomes an egg."],
        "source_references": ["book#butterfly"],
        "personal_fact_keys": ["favorite:butterfly"],
        "locale": "en",
        "direction": "ltr",
        "use_display_name": False,
    }
    value.update(overrides)
    return value


def test_admission_assigns_deterministic_support_ids_and_frozen_digest() -> None:
    admitted = admit_visual_order(
        _order(),
        authorized_source_references={"book#butterfly": {"text": "A larva becomes a pupa."}},
        visual_personalization_catalog={"favorite:butterfly": {"category": "FAVORITE", "display_statement": "Likes butterflies"}},
        core_profile={"age_years": 10, "grade_level": "5", "display_name": "Lina"},
    )

    assert [item["id"] for item in admitted.semantic_alignment["required_semantics"]] == ["F1", "F2", "F3"]
    assert [item["id"] for item in admitted.semantic_alignment["required_relations"]] == ["R1", "R2", "R3"]
    assert admitted.frozen_composition_pack["grounding"]["origin"] == "RETRIEVED_SOURCE"
    assert admitted.frozen_composition_pack["visual_learner_context"] == {
        "version": "visual-learner-context-v1",
        "core_profile": {"age_years": 10, "grade_level": "5"},
        "selected_personal_facts": [{"fact_key": "favorite:butterfly", "category": "FAVORITE", "display_statement": "Likes butterflies"}],
    }
    assert len(admitted.order_digest) == 64


@pytest.mark.parametrize("field, value", [
    ("pattern", "DIAGRAM"),
    ("required_semantics", ["React renderer"]),
    ("source_references", ["unauthorized#source"]),
    ("personal_fact_keys", ["unknown:fact"]),
])
def test_admission_rejects_unsupported_or_unauthorized_meaning(field: str, value: object) -> None:
    with pytest.raises(VisualOrderAdmissionError):
        admit_visual_order(
            _order(**{field: value}),
            authorized_source_references={"book#butterfly": {"text": "A larva becomes a pupa."}},
            visual_personalization_catalog={"favorite:butterfly": {"category": "FAVORITE", "display_statement": "Likes butterflies"}},
            core_profile={},
        )


def test_no_source_order_is_admitted_with_explicit_model_knowledge_grounding() -> None:
    admitted = admit_visual_order(
        _order(source_references=[], personal_fact_keys=[]),
        authorized_source_references={},
        visual_personalization_catalog={},
        core_profile={},
    )
    assert admitted.frozen_composition_pack["grounding"] == {"origin": "ADMITTED_TUTOR_ORDER", "excerpts": []}


@pytest.mark.parametrize(
    "pattern,interaction_goal,expected_identity",
    [
        ("SPATIAL_MANIPULATION", "PLACE_OBJECT", "canvas-spatial-capability-pack-v1"),
        ("MATH_VISUALIZATION", "CONSTRUCT_POINT", "canvas-math-visualization-capability-pack-v1"),
        ("MATH_INPUT", "AUTHOR_EXPRESSION", "canvas-math-input-capability-pack-v1"),
    ],
)
def test_v2_admission_freezes_exact_non_process_capability_without_technology(pattern, interaction_goal, expected_identity):
    order = _order(
        version="workspace-visual-order-v2",
        pattern=pattern,
        topology=None,
        interaction_goal=interaction_goal,
        source_references=[],
        personal_fact_keys=[],
    )
    admitted = admit_visual_order(order, authorized_source_references={}, visual_personalization_catalog={}, core_profile={"grade_level": "5"})
    pack = admitted.frozen_composition_pack
    assert pack["version"] == "frozen-composition-pack-v3"
    assert pack["capability_pack"]["identity"] == expected_identity
    assert not any(name in repr(pack).lower() for name in ("konva", "jsxgraph", "mathlive", "renderer"))


def test_v2_pattern_and_interaction_goal_must_match():
    with pytest.raises(VisualOrderAdmissionError):
        admit_visual_order(
            _order(version="workspace-visual-order-v2", pattern="MATH_INPUT", topology=None, interaction_goal="PLACE_OBJECT"),
            authorized_source_references={"book#butterfly": {"text": "A larva becomes a pupa."}},
            visual_personalization_catalog={"favorite:butterfly": {"category": "FAVORITE", "display_statement": "Likes butterflies"}},
            core_profile={},
        )


def test_math_visualization_frozen_pack_advertises_the_exact_ten_unit_plane() -> None:
    admitted = admit_visual_order(
        _order(
            version="workspace-visual-order-v2", pattern="MATH_VISUALIZATION", topology=None,
            interaction_goal="CONSTRUCT_POINT", source_references=[], personal_fact_keys=[],
        ),
        authorized_source_references={}, visual_personalization_catalog={}, core_profile={},
    )

    assert admitted.frozen_composition_pack["capability_pack"]["coordinate_bounds"] == [-10, 10]
