"""Deterministic planning contracts for bounded semantic extraction."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.content.semantic_contract import SemanticContractError, parse_semantic_output, validate_semantic_output
from services.content.semantics import _SHARED_INSTRUCTIONS, _plan_semantic_batches


def _item(
    key: str,
    order: int,
    *,
    parent: str | None = None,
    item_type: str = "text",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=key,
        item_key=key,
        parent_id=parent,
        reading_order=order,
        item_type=item_type,
        page_number=None,
        heading_level=None,
        source_ref=f"fixture#item={key}",
        text=key,
        caption_text=None,
        attributes={},
    )


def _keys(plans: list[object]) -> list[str]:
    return [item.item_key for plan in plans for item in plan.structural_items]


def test_prompt_makes_reference_only_context_and_current_batch_provenance_explicit() -> None:
    assert "reference-only" in _SHARED_INSTRUCTIONS
    assert "Do not re-emit" in _SHARED_INSTRUCTIONS
    assert "MUST contain at least one" in _SHARED_INSTRUCTIONS


@pytest.mark.parametrize(
    "path",
    [
        "scripts/verify_eureka_semantic_representation.py",
        "scripts/prepare_eureka_retrieval_golden.py",
        "scripts/prepare_eureka_retrieval_multiregion.py",
    ],
)
def test_eureka_semantic_helpers_pass_semantic_run_to_extract_batch(path: str) -> None:
    tree = ast.parse(Path(path).read_text())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "_extract_batch"
    ]

    assert calls
    assert all(any(keyword.arg == "semantic_run" for keyword in call.keywords) for call in calls)


def test_planner_has_exact_disjoint_coverage_and_preserves_global_reading_order() -> None:
    items = [
        _item("#/body", 0, item_type="unspecified"),
        _item("title", 1, parent="#/body", item_type="section_header"),
        _item("group", 2, parent="#/body", item_type="list"),
        _item("child-a", 3, parent="group"),
        _item("child-b", 4, parent="group"),
        _item("footer", 5, parent="#/body"),
    ]

    plans = _plan_semantic_batches(items, max_items=3)

    assert _keys(plans) == [item.item_key for item in items]
    assert len(_keys(plans)) == len(set(_keys(plans))) == len(items)
    assert [len(plan.structural_items) for plan in plans] == [2, 3, 1]


def test_nested_groups_are_one_disjoint_coherent_planning_unit() -> None:
    items = [
        _item("#/body", 0, item_type="unspecified"),
        _item("outer", 1, parent="#/body", item_type="form_area"),
        _item("inner", 2, parent="outer", item_type="list"),
        _item("leaf", 3, parent="inner"),
        _item("next", 4, parent="#/body"),
    ]

    plans = _plan_semantic_batches(items, max_items=10)

    assert [[item.item_key for item in plan.structural_items] for plan in plans] == [
        ["#/body", "outer", "inner", "leaf", "next"]
    ]
    assert _keys(plans).count("inner") == 1
    assert _keys(plans).count("leaf") == 1


def test_coherent_group_that_fits_stays_together_at_the_former_eureka_boundary() -> None:
    items = [_item("#/body", 0, item_type="unspecified")]
    items.extend(_item(f"leading-{order}", order, parent="#/body") for order in range(1, 39))
    items.extend(
        [
            _item("#/groups/7", 39, parent="#/body", item_type="list"),
            _item("#/texts/47", 40, parent="#/groups/7", item_type="list_item"),
            _item("#/texts/48", 41, parent="#/groups/7", item_type="list_item"),
            _item("#/texts/59", 42, parent="#/groups/7", item_type="list_item"),
            _item("after", 43, parent="#/body"),
        ]
    )

    plans = _plan_semantic_batches(items, max_items=24)
    boundary_plan = next(plan for plan in plans if "#/groups/7" in {item.item_key for item in plan.structural_items})

    assert {item.item_key for item in boundary_plan.structural_items} >= {
        "#/groups/7", "#/texts/47", "#/texts/48", "#/texts/59"
    }


def test_oversized_group_continues_deterministically_with_non_citable_parent_context() -> None:
    items = [_item("#/body", 0, item_type="unspecified"), _item("group", 1, parent="#/body", item_type="list")]
    items.extend(_item(f"child-{order}", order, parent="group") for order in range(2, 14))

    first = _plan_semantic_batches(items, max_items=5)
    second = _plan_semantic_batches(items, max_items=5)

    assert [[item.item_key for item in plan.structural_items] for plan in first] == [
        ["#/body"],
        ["group", "child-2", "child-3", "child-4", "child-5"],
        ["child-6", "child-7", "child-8", "child-9", "child-10"],
        ["child-11", "child-12", "child-13"],
    ]
    assert [[item.item_key for item in plan.structural_items] for plan in second] == [
        [item.item_key for item in plan.structural_items] for plan in first
    ]
    assert [item.item_key for item in first[2].continuation_parent_items] == ["group"]
    assert [item.item_key for item in first[3].continuation_parent_items] == ["group"]
    assert "group" not in {item.item_key for item in first[2].structural_items}


@pytest.mark.parametrize("source_keys", [[], ["known-parent"]])
def test_reference_context_cannot_supply_or_replace_current_batch_provenance(source_keys: list[str]) -> None:
    text = {
        "schema_version": "grade5-math-semantic-schema-v1",
        "items": [
            {
                "semantic_key": "new-exercise",
                "semantic_type": "EXERCISE",
                "title": "New exercise",
                "description": None,
                "normalized_concept_key": None,
                "parent_semantic_key": "known-parent",
                "structural_item_keys": source_keys,
                "sibling_order": 0,
                "metadata": {},
            }
        ],
        "unclassified_structural_item_keys": ["current-source"],
    }

    if not source_keys:
        with pytest.raises(SemanticContractError, match="at least 1 item"):
            parse_semantic_output(__import__("json").dumps(text))
        return

    output = parse_semantic_output(__import__("json").dumps(text))
    with pytest.raises(SemanticContractError, match="unknown structural item"):
        validate_semantic_output(
            output,
            available_structural_item_keys={"current-source"},
            allowed_parent_semantic_keys={"known-parent"},
        )
