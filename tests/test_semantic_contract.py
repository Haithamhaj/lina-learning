"""Contract tests for project-owned Grade 5 Math semantic model output."""

from __future__ import annotations

import json

import pytest

from services.content.semantic_contract import (
    SemanticContractError,
    parse_semantic_output,
    validate_semantic_output,
)


def _output(*, items: list[dict[str, object]], unclassified: list[str]) -> str:
    return json.dumps(
        {
            "schema_version": "grade5-math-semantic-schema-v1",
            "items": items,
            "unclassified_structural_item_keys": unclassified,
        }
    )


def _item(
    key: str,
    semantic_type: str,
    source_keys: list[str],
    *,
    parent: str | None = None,
    order: int = 0,
) -> dict[str, object]:
    return {
        "semantic_key": key,
        "semantic_type": semantic_type,
        "title": key.replace("-", " ").title(),
        "description": None,
        "normalized_concept_key": key if semantic_type == "CONCEPT" else None,
        "parent_semantic_key": parent,
        "structural_item_keys": source_keys,
        "sibling_order": order,
        "metadata": {},
    }


def test_contract_preserves_explicit_educational_types_and_complete_batch_accounting() -> None:
    text = _output(
        items=[
            _item("module-1", "UNIT", ["root"]),
            _item("lesson-1", "LESSON", ["lesson"], parent="module-1"),
            _item("place-value", "CONCEPT", ["concept"], parent="lesson-1"),
            _item("objective-1", "OBJECTIVE", ["objective"], parent="place-value"),
            _item("explanation-1", "EXPLANATION", ["explanation"], parent="place-value"),
            _item("example-1", "EXAMPLE", ["example"], parent="place-value"),
            _item("practice-1", "EXERCISE", ["exercise"], parent="lesson-1"),
            _item("vocabulary-1", "VOCABULARY", ["vocabulary"], parent="place-value"),
            _item("diagram-1", "FIGURE", ["figure"], parent="lesson-1"),
            _item("table-1", "TABLE", ["table"], parent="lesson-1"),
            _item("formula-1", "FORMULA", ["formula"], parent="lesson-1"),
        ],
        unclassified=["decorative"],
    )

    output = parse_semantic_output(text)
    validate_semantic_output(
        output,
        available_structural_item_keys={
            "root", "lesson", "concept", "objective", "explanation", "example",
            "exercise", "vocabulary", "figure", "table", "formula", "decorative",
        },
    )

    assert [item.semantic_type for item in output.items] == [
        "UNIT", "LESSON", "CONCEPT", "OBJECTIVE", "EXPLANATION", "EXAMPLE",
        "EXERCISE", "VOCABULARY", "FIGURE", "TABLE", "FORMULA",
    ]


@pytest.mark.parametrize(
    ("items", "available_keys", "message"),
    [
        (
            [_item("duplicate", "UNIT", ["root"]), _item("duplicate", "LESSON", ["lesson"])],
            {"root", "lesson"},
            "Duplicate semantic key",
        ),
        (
            [_item("lesson", "LESSON", ["lesson"], parent="unknown-unit")],
            {"lesson"},
            "missing parent",
        ),
        (
            [_item("lesson", "LESSON", ["not-in-tree"])],
            {"lesson"},
            "unknown structural item",
        ),
    ],
)
def test_contract_rejects_invalid_stable_relationships(
    items: list[dict[str, object]], available_keys: set[str], message: str
) -> None:
    output = parse_semantic_output(_output(items=items, unclassified=list(available_keys - {"lesson"})))

    with pytest.raises(SemanticContractError, match=message):
        validate_semantic_output(output, available_structural_item_keys=available_keys)


def test_contract_rejects_unaccounted_structural_items_without_an_arbitrary_ratio() -> None:
    output = parse_semantic_output(
        _output(items=[_item("module-1", "UNIT", ["root"])], unclassified=[])
    )

    with pytest.raises(SemanticContractError, match="unaccounted structural items"):
        validate_semantic_output(output, available_structural_item_keys={"root", "ignored"})


def test_contract_accepts_an_all_unclassified_decorative_batch() -> None:
    output = parse_semantic_output(
        _output(items=[], unclassified=["decorative-picture", "footer"])
    )

    validate_semantic_output(
        output,
        available_structural_item_keys={"decorative-picture", "footer"},
    )

    assert output.items == []


def test_contract_rejects_all_unclassified_batch_with_missing_source_accounting() -> None:
    output = parse_semantic_output(
        _output(items=[], unclassified=["decorative-picture"])
    )

    with pytest.raises(SemanticContractError, match="unaccounted structural items"):
        validate_semantic_output(
            output,
            available_structural_item_keys={"decorative-picture", "footer"},
        )
