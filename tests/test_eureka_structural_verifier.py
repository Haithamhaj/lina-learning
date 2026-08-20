"""Behavior tests for the real-document TASK-011 structural verifier."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.content.structural_contract import NormalizedStructuralItem


def _verifier_module() -> object:
    path = Path(__file__).parents[1] / "scripts" / "verify_eureka_structural_representation.py"
    spec = importlib.util.spec_from_file_location("task011_eureka_verifier", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalized_items() -> list[NormalizedStructuralItem]:
    return [
        NormalizedStructuralItem(
            item_key="#/body", parent_item_key=None, sibling_order=0, reading_order=0,
            hierarchy_depth=0, item_type="unspecified", text=None, caption_text=None,
            caption_item_keys=(), heading_level=None, page_number=None,
            source_ref="fixture.pdf#item=0", provenance={"locations": []}, attributes={},
        ),
        NormalizedStructuralItem(
            item_key="#/tables/0", parent_item_key="#/body", sibling_order=0, reading_order=1,
            hierarchy_depth=1, item_type="table", text=None, caption_text=None,
            caption_item_keys=(), heading_level=None, page_number=2,
            source_ref="fixture.pdf#page=2:item=1",
            provenance={"locations": [{"page_no": 2, "bbox": {"l": 1, "t": 2, "r": 3, "b": 4}}]},
            attributes={},
        ),
    ]


def _persisted_rows(**child_overrides: object) -> list[SimpleNamespace]:
    root = SimpleNamespace(
        id="root-id", item_key="#/body", parent_id=None, sibling_order=0, reading_order=0,
        hierarchy_depth=0, item_type="unspecified", page_number=None,
        source_ref="fixture.pdf#item=0", provenance={"locations": []},
    )
    child = SimpleNamespace(
        id="table-id", item_key="#/tables/0", parent_id="root-id", sibling_order=0,
        reading_order=1, hierarchy_depth=1, item_type="table", page_number=2,
        source_ref="fixture.pdf#page=2:item=1",
        provenance={"locations": [{"page_no": 2, "bbox": {"l": 1, "t": 2, "r": 3, "b": 4}}]},
    )
    for field, value in child_overrides.items():
        setattr(child, field, value)
    return [root, child]


def test_verifier_accepts_matching_persisted_structural_relationships() -> None:
    """Fails if the verifier rejects a persisted tree that matches the adapter contract."""

    verifier = _verifier_module()

    verifier._assert_persisted_matches_normalized(_persisted_rows(), _normalized_items())


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"parent_id": None}, "parent"),
        ({"sibling_order": 1}, "sibling"),
        ({"reading_order": 2}, "reading"),
        ({"item_type": "text"}, "type"),
        ({"page_number": 3}, "page"),
        ({"provenance": {"locations": [{"page_no": 3}]}}, "provenance"),
    ],
)
def test_verifier_rejects_mismatched_persisted_structural_fields(
    override: dict[str, object], message: str
) -> None:
    """Fails if persisted hierarchy/order/type/provenance drift is not detected."""

    verifier = _verifier_module()

    with pytest.raises(SystemExit, match=message):
        verifier._assert_persisted_matches_normalized(_persisted_rows(**override), _normalized_items())
