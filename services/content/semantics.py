"""Deterministic Grade 5 Math semantic mapping over Docling structure."""

from __future__ import annotations

import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from services.model_gateway.gateway import ModelGateway
from services.platform.db.models import ContentBlock, ContentDocument, CurriculumNode, ModelTask


SEMANTICS_VERSION = "grade5-math-semantic-v1"


def extract_educational_semantics(
    session: Session,
    *,
    document: ContentDocument,
    gateway: ModelGateway,
) -> list[CurriculumNode]:
    """Create explicit Unit/Lesson/Exercise nodes without confusing layout for meaning."""

    blocks = session.execute(
        select(ContentBlock)
        .where(ContentBlock.document_id == document.id)
        .order_by(ContentBlock.page_number, ContentBlock.source_ref)
    ).scalars().all()
    if not blocks:
        raise ValueError("Structural content is required before semantic extraction.")
    gateway.execute(ModelTask.CURRICULUM_SEMANTICS, {"document_id": str(document.id), "block_count": len(blocks)})
    session.execute(delete(CurriculumNode).where(CurriculumNode.document_id == document.id))
    nodes: list[CurriculumNode] = []
    parent_id = None
    for block in blocks:
        title = block.text.strip()
        normalized = title.lower()
        node_type = None
        if "module" in normalized or "unit" in normalized:
            node_type = "UNIT"
        elif "lesson" in normalized:
            node_type = "LESSON"
        elif block.block_type in {"list_item", "table"} and re.search(r"\b(use|solve|explain|write|draw)\b", normalized):
            node_type = "EXERCISE"
        if node_type is None:
            continue
        node = CurriculumNode(
            document_id=document.id,
            processing_run_id=block.processing_run_id,
            parent_id=parent_id,
            node_type=node_type,
            title=title[:500],
            source_ref=block.source_ref,
            page_number=block.page_number,
        )
        session.add(node)
        session.flush()
        nodes.append(node)
        if node_type in {"UNIT", "LESSON"}:
            parent_id = node.id
    return nodes
