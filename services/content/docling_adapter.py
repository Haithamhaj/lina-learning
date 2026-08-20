"""Docling boundary for a source-linked structural representation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter

from .structural_contract import NormalizedStructuralItem

def extract_structural_markdown(source: str) -> str:
    """Use Docling's Markdown pipeline and retain its normalized structure."""

    return _convert_markdown(source).document.export_to_markdown()


def extract_pdf_structural_markdown(content: bytes) -> str:
    """Convert an uploaded PDF while keeping its original in object storage."""

    return _convert_pdf(content).document.export_to_markdown()


def extract_structural_items(
    *,
    content_type: str,
    content: bytes,
    filename: str,
) -> list[NormalizedStructuralItem]:
    """Convert a source document into the project-owned structural contract."""

    if content_type == "text/markdown":
        result = _convert_markdown(content.decode("utf-8"))
    elif content_type == "application/pdf":
        result = _convert_pdf(content)
    else:
        raise ValueError("The structural processor does not support this content type.")

    return normalize_docling_document(result.document, filename=filename)


def normalize_docling_document(document: Any, *, filename: str) -> list[NormalizedStructuralItem]:
    """Translate Docling's tree into a stable, queryable Lina contract.

    Keys are the processor's ``self_ref`` when present, which gives a stable
    identity within one run.  The fallback is deterministic reading order for
    processors or fixtures that do not expose a reference.  Parent links,
    sibling order, layout provenance and item-specific payloads are retained
    without leaking a Docling object past this adapter.
    """

    raw_items = list(document.iterate_items(with_groups=True))
    key_by_object_id: dict[int, str] = {}
    for reading_order, (item, _) in enumerate(raw_items):
        key_by_object_id[id(item)] = _item_key(item, reading_order)

    sibling_counts: dict[str | None, int] = {}
    normalized: list[NormalizedStructuralItem] = []
    item_text_by_key: dict[str, str] = {}
    pending_captions: list[tuple[int, tuple[str, ...]]] = []
    for reading_order, (item, depth) in enumerate(raw_items):
        item_key = key_by_object_id[id(item)]
        parent_item_key = _reference_key(getattr(item, "parent", None))
        sibling_order = sibling_counts.get(parent_item_key, 0)
        sibling_counts[parent_item_key] = sibling_order + 1
        item_type = _item_type(item)
        text = _item_text(item)
        if text:
            item_text_by_key[item_key] = text
        locations = [_normalize_provenance(entry) for entry in (getattr(item, "prov", ()) or ())]
        page_number = next(
            (
                location["page_no"]
                for location in locations
                if isinstance(location.get("page_no"), int)
            ),
            None,
        )
        source_ref = f"{filename}#item={reading_order}"
        if page_number is not None:
            source_ref = f"{filename}#page={page_number}:item={reading_order}"
        caption_item_keys = tuple(
            reference
            for reference in (_reference_key(value) for value in (getattr(item, "captions", ()) or ()))
            if reference is not None
        )
        normalized.append(
            NormalizedStructuralItem(
                item_key=item_key,
                parent_item_key=parent_item_key,
                sibling_order=sibling_order,
                reading_order=reading_order,
                hierarchy_depth=depth,
                item_type=item_type,
                text=text,
                caption_text=None,
                caption_item_keys=caption_item_keys,
                heading_level=depth if item_type in {"title", "section_header"} else None,
                page_number=page_number,
                source_ref=source_ref,
                provenance={"locations": locations},
                attributes=_item_attributes(item, item_type),
            )
        )
        pending_captions.append((len(normalized) - 1, caption_item_keys))

    for item_index, caption_item_keys in pending_captions:
        if not caption_item_keys:
            continue
        caption_text = "\n".join(
            item_text_by_key[caption_key]
            for caption_key in caption_item_keys
            if caption_key in item_text_by_key
        ) or None
        normalized[item_index] = NormalizedStructuralItem(
            **{**normalized[item_index].__dict__, "caption_text": caption_text}
        )
    return normalized


def _item_key(item: Any, reading_order: int) -> str:
    value = getattr(item, "self_ref", None)
    reference = _reference_key(value)
    return reference or f"item:{reading_order}"


def _reference_key(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    reference = getattr(value, "cref", None)
    return reference if isinstance(reference, str) and reference else None


def _item_type(item: Any) -> str:
    label = getattr(item, "label", None)
    value = getattr(label, "value", label)
    return str(value or type(item).__name__).lower()


def _item_text(item: Any) -> str | None:
    text = getattr(item, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    return None


def _normalize_provenance(entry: Any) -> dict[str, object]:
    result: dict[str, object] = {}
    page_no = getattr(entry, "page_no", None)
    if isinstance(page_no, int):
        result["page_no"] = page_no
    bbox = getattr(entry, "bbox", None)
    if bbox is not None:
        result["bbox"] = _json_value(bbox)
    charspan = getattr(entry, "charspan", None)
    if charspan is not None:
        result["charspan"] = _json_value(charspan)
    return result


def _item_attributes(item: Any, item_type: str) -> dict[str, object]:
    attributes: dict[str, object] = {"docling_label": item_type}
    content_layer = getattr(item, "content_layer", None)
    if content_layer is not None:
        attributes["content_layer"] = _json_value(content_layer)
    data = getattr(item, "data", None)
    if data is not None:
        attributes["structured_data"] = _json_value(data)
    return attributes


def _json_value(value: Any) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    known_layout_fields = ("l", "t", "r", "b", "coord_origin")
    if any(hasattr(value, field) for field in known_layout_fields):
        return {
            field: _json_value(getattr(value, field))
            for field in known_layout_fields
            if hasattr(value, field)
        }
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _json_value(model_dump(mode="json"))
    if hasattr(value, "__dict__"):
        return {
            key: _json_value(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, (str, int, float, bool)):
        return enum_value
    return str(value)


def _convert_markdown(source: str) -> Any:
    return DocumentConverter().convert(
        DocumentStream(name="fixture.md", stream=BytesIO(source.encode("utf-8")))
    )


def _convert_pdf(content: bytes) -> Any:
    with NamedTemporaryFile(suffix=".pdf") as source:
        source.write(content)
        source.flush()
        return DocumentConverter().convert(Path(source.name))
