"""Unit tests for explicit TASK-012 Eureka semantic-golden assertions."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.content.semantic_contract import SEMANTIC_SCHEMA_VERSION, SemanticContractError, SemanticExtractionOutput


def _load_verifier():
    path = Path("scripts/verify_eureka_semantic_representation.py")
    spec = importlib.util.spec_from_file_location("eureka_semantic_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _structural(key: str, page: int) -> SimpleNamespace:
    return SimpleNamespace(item_key=key, page_number=page, source_ref=f"Eureka#page={page}:item={key}")


def _item(key: str, semantic_type: str, sources: list[str], *, title: str = "Label", description: str | None = None):
    return {
        "semantic_key": key,
        "semantic_type": semantic_type,
        "title": title,
        "description": description,
        "normalized_concept_key": "place-value" if semantic_type == "CONCEPT" else None,
        "parent_semantic_key": None,
        "structural_item_keys": sources,
        "sibling_order": 0,
        "metadata": {},
    }


def _output() -> SemanticExtractionOutput:
    return SemanticExtractionOutput.model_validate(
        {
            "schema_version": SEMANTIC_SCHEMA_VERSION,
            "items": [
                _item("unit", "UNIT", ["#/texts/1"], title="Grade 5 Module 1"),
                _item("lesson", "LESSON", ["#/texts/26"], title="Place Value Practice"),
                _item("concept", "CONCEPT", ["#/texts/26"], title="Place Value"),
                _item("objective", "OBJECTIVE", ["#/texts/26"]),
                _item("example", "EXAMPLE", ["#/texts/27"]),
                _item("exercise", "EXERCISE", ["#/texts/36"]),
                _item("figure", "FIGURE", ["#/pictures/1"]),
            ],
            "unclassified_structural_item_keys": [],
        }
    )


def test_eureka_golden_requires_real_educational_types_and_page_source_links() -> None:
    verifier = _load_verifier()
    items = [
        _structural("#/texts/1", 1), _structural("#/texts/26", 2),
        _structural("#/texts/27", 2), _structural("#/texts/36", 2),
        _structural("#/pictures/1", 2),
    ]

    verifier._assert_eureka_golden(_output(), items)


def test_eureka_golden_rejects_example_without_expected_real_source() -> None:
    verifier = _load_verifier()
    output = _output()
    output.items[4].structural_item_keys = ["#/texts/26"]
    items = [
        _structural("#/texts/1", 1), _structural("#/texts/26", 2),
        _structural("#/texts/27", 2), _structural("#/texts/36", 2),
        _structural("#/pictures/1", 2),
    ]

    with pytest.raises(SemanticContractError, match="EXAMPLE"):
        verifier._assert_eureka_golden(output, items)
