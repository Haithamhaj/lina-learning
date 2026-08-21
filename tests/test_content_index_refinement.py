from types import SimpleNamespace

from services.content.indexing import refine_semantic_sources


def test_semantic_refinement_keeps_multi_source_entity_whole_when_it_fits() -> None:
    first = SimpleNamespace(text="a" * 900, caption_text=None, page_number=4)
    second = SimpleNamespace(text="b" * 900, caption_text=None, page_number=5)
    source_one = SimpleNamespace(structural_item_key="first")
    source_two = SimpleNamespace(structural_item_key="second")

    refined = refine_semantic_sources([(source_one, first), (source_two, second)], maximum_characters=2000)

    assert [(content, [source.structural_item_key for source, _ in sources]) for content, sources in refined] == [
        ("a" * 900 + "\n" + "b" * 900, ["first", "second"]),
    ]


def test_semantic_refinement_keeps_exact_structural_sources_per_sub_block() -> None:
    first = SimpleNamespace(text="a" * 1500, caption_text=None)
    second = SimpleNamespace(text="b" * 1500, caption_text=None)
    source_one = SimpleNamespace(structural_item_key="first")
    source_two = SimpleNamespace(structural_item_key="second")

    refined = refine_semantic_sources([(source_one, first), (source_two, second)], maximum_characters=2000)

    assert [(content, [source.structural_item_key for source, _ in sources]) for content, sources in refined] == [
        ("a" * 1500, ["first"]),
        ("b" * 1500, ["second"]),
    ]
