"""Docling boundary for a source-linked structural representation."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter


@dataclass(frozen=True)
class StructuralItem:
    """One reading-order item from Docling with source provenance intact."""

    text: str
    item_type: str
    page_number: int | None
    source_ref: str
    attributes: dict[str, object]


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
) -> list[StructuralItem]:
    """Normalize Docling reading order without discarding page/type provenance."""

    if content_type == "text/markdown":
        result = _convert_markdown(content.decode("utf-8"))
    elif content_type == "application/pdf":
        result = _convert_pdf(content)
    else:
        raise ValueError("The structural processor does not support this content type.")

    items: list[StructuralItem] = []
    for item_index, (item, _) in enumerate(result.document.iterate_items()):
        item_type = str(getattr(item, "label", type(item).__name__)).lower()
        provenance = list(getattr(item, "prov", ()) or ())
        page_number = getattr(provenance[0], "page_no", None) if provenance else None
        item_text = getattr(item, "text", None)
        item_text = item_text.strip() if isinstance(item_text, str) else f"[{item_type}]"
        if not item_text:
            continue
        source_ref = f"{filename}#item={item_index}"
        if isinstance(page_number, int):
            source_ref = f"{filename}#page={page_number}:item={item_index}"
        items.append(
            StructuralItem(
                text=item_text,
                item_type=item_type,
                page_number=page_number if isinstance(page_number, int) else None,
                source_ref=source_ref,
                attributes={
                    "label": item_type,
                    "provenance_count": len(provenance),
                    "has_figure": item_type in {"picture", "figure"},
                    "has_table": item_type == "table",
                    "has_formula": item_type == "formula",
                },
            )
        )
    return items


def _convert_markdown(source: str) -> Any:
    return DocumentConverter().convert(
        DocumentStream(name="fixture.md", stream=BytesIO(source.encode("utf-8")))
    )


def _convert_pdf(content: bytes) -> Any:
    with NamedTemporaryFile(suffix=".pdf") as source:
        source.write(content)
        source.flush()
        return DocumentConverter().convert(Path(source.name))
