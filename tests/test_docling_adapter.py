"""Contract tests for the project-owned Docling structural adapter."""

from __future__ import annotations

from dataclasses import dataclass, field

from services.content.docling_adapter import extract_structural_items, normalize_docling_document


@dataclass(frozen=True)
class _Ref:
    cref: str


@dataclass(frozen=True)
class _Provenance:
    page_no: int
    bbox: object | None = None


@dataclass
class _Item:
    self_ref: str
    label: str
    text: str | None = None
    parent: _Ref | None = None
    prov: list[_Provenance] = field(default_factory=list)
    captions: list[_Ref] = field(default_factory=list)
    data: object | None = None


class _Document:
    def __init__(self, pairs: list[tuple[_Item, int]]) -> None:
        self._pairs = pairs

    def iterate_items(self, *, with_groups: bool = False):
        assert with_groups is True
        return iter(self._pairs)


def _controlled_document() -> _Document:
    body = _Item("#/body", "unspecified")
    title = _Item("#/texts/0", "title", "Module 1", _Ref("#/body"), [_Provenance(1)])
    section = _Item("#/texts/1", "section_header", "Topic A", _Ref("#/body"), [_Provenance(1)])
    subsection = _Item("#/texts/2", "section_header", "Lesson A.1", _Ref("#/body"), [_Provenance(1)])
    paragraph = _Item("#/texts/3", "text", "Read the model.", _Ref("#/body"), [_Provenance(1)])
    list_group = _Item("#/groups/0", "list", parent=_Ref("#/body"))
    list_item = _Item("#/texts/4", "list_item", "Count tenths.", _Ref("#/groups/0"), [_Provenance(1)])
    table = _Item("#/tables/0", "table", parent=_Ref("#/body"), prov=[_Provenance(2)])
    picture = _Item(
        "#/pictures/0",
        "picture",
        parent=_Ref("#/body"),
        prov=[_Provenance(2)],
        captions=[_Ref("#/texts/5")],
    )
    caption = _Item("#/texts/5", "caption", "Place-value chart", _Ref("#/body"), [_Provenance(2)])
    formula = _Item("#/texts/6", "formula", "10 × 4 = 40", _Ref("#/body"), [_Provenance(2)])
    return _Document(
        [
            (body, 0),
            (title, 1),
            (section, 1),
            (subsection, 2),
            (paragraph, 2),
            (list_group, 2),
            (list_item, 3),
            (table, 1),
            (picture, 1),
            (caption, 1),
            (formula, 1),
        ]
    )


def test_normalized_contract_preserves_controlled_tree_order_types_and_provenance() -> None:
    """Fails if the adapter regresses to flattened reading-order blocks."""

    items = normalize_docling_document(_controlled_document(), filename="fixture.pdf")
    by_key = {item.item_key: item for item in items}

    assert [item.item_key for item in items] == [
        "#/body",
        "#/texts/0",
        "#/texts/1",
        "#/texts/2",
        "#/texts/3",
        "#/groups/0",
        "#/texts/4",
        "#/tables/0",
        "#/pictures/0",
        "#/texts/5",
        "#/texts/6",
    ]
    assert by_key["#/texts/4"].parent_item_key == "#/groups/0"
    assert by_key["#/texts/4"].sibling_order == 0
    assert by_key["#/texts/4"].reading_order == 6
    assert by_key["#/texts/4"].page_number == 1
    assert by_key["#/texts/4"].source_ref == "fixture.pdf#page=1:item=6"
    assert by_key["#/texts/2"].heading_level == 2
    assert by_key["#/groups/0"].item_type == "list"
    assert by_key["#/tables/0"].item_type == "table"
    assert by_key["#/pictures/0"].item_type == "picture"
    assert by_key["#/pictures/0"].caption_item_keys == ("#/texts/5",)
    assert by_key["#/texts/6"].item_type == "formula"


def test_normalized_contract_retains_layout_provenance_when_docling_supplies_it() -> None:
    """Fails if page layout data is discarded while normalizing an item."""

    bbox = type("BBox", (), {"l": 10, "t": 20, "r": 30, "b": 40, "coord_origin": "TOPLEFT"})()
    item = _Item("#/texts/1", "text", "A paragraph", _Ref("#/body"), [_Provenance(3, bbox)])
    items = normalize_docling_document(
        _Document([(_Item("#/body", "unspecified"), 0), (item, 1)]),
        filename="fixture.pdf",
    )

    assert items[1].provenance == {
        "locations": [
            {
                "page_no": 3,
                "bbox": {"l": 10, "t": 20, "r": 30, "b": 40, "coord_origin": "TOPLEFT"},
            }
        ]
    }


def test_real_docling_markdown_output_retains_groups_headings_and_tables() -> None:
    """Fails if Docling output is flattened while crossing the adapter boundary."""

    items = extract_structural_items(
        content_type="text/markdown",
        content=(
            b"# Module 1\n\n## Lesson 1\n\nRead the example.\n\n"
            b"- Count tenths\n- Compare values\n\n"
            b"| Fraction | Equivalent |\n| --- | --- |\n| 1/2 | 2/4 |\n"
        ),
        filename="fixture.md",
    )
    by_key = {item.item_key: item for item in items}

    assert any(item.item_type == "title" and item.text == "Module 1" for item in items)
    assert any(item.item_type == "section_header" and item.text == "Lesson 1" for item in items)
    list_group = next(item for item in items if item.item_type == "list")
    list_items = [item for item in items if item.parent_item_key == list_group.item_key]
    assert [item.text for item in list_items] == ["Count tenths", "Compare values"]
    assert [item.sibling_order for item in list_items] == [0, 1]
    table = next(item for item in items if item.item_type == "table")
    assert table.attributes["structured_data"]["num_rows"] == 2
    assert table.attributes["structured_data"]["num_cols"] == 2
    assert by_key[list_group.item_key].hierarchy_depth < list_items[0].hierarchy_depth
