"""Project-owned contract for a versioned document structural artifact.

This module deliberately contains no Docling imports.  Consumers in later
Content tasks receive this stable contract rather than document-processor SDK
objects, so a processor upgrade can be isolated to the adapter boundary.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedStructuralItem:
    """One source-linked node in a processor-normalized document tree."""

    item_key: str
    parent_item_key: str | None
    sibling_order: int
    reading_order: int
    hierarchy_depth: int
    item_type: str
    text: str | None
    caption_text: str | None
    caption_item_keys: tuple[str, ...]
    heading_level: int | None
    page_number: int | None
    source_ref: str
    provenance: dict[str, object]
    attributes: dict[str, object]
