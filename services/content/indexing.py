"""Build versioned, provenance-first PostgreSQL retrieval blocks for TASK-013."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.db.models import ContentDocument, ContentIndexRun, ContentProcessingRun, ContentSemanticItem, ContentSemanticItemSource, ContentSemanticProcessingRun, DocumentStructuralItem, IndexedContentBlock, IndexedContentBlockSource, ModelTask

BLOCK_SCHEMA_VERSION = "semantic-structural-blocks-v2"
INDEX_SETTINGS_VERSION = "boundary-refinement-v2"
MAX_BLOCK_CHARS = 2000


def build_content_index(session: Session, *, document: ContentDocument, gateway: ModelGateway, structural_run: ContentProcessingRun | None = None, semantic_run: ContentSemanticProcessingRun | None = None, block_schema_version: str = BLOCK_SCHEMA_VERSION, settings_version: str = INDEX_SETTINGS_VERSION) -> ContentIndexRun:
    """Index completed structural content, optionally preserving semantic enrichment."""
    route = gateway.route_for(ModelTask.EMBEDDING)
    if semantic_run is not None:
        if document.id != semantic_run.document_id or semantic_run.status != "COMPLETED":
            raise ValueError("A completed semantic run for this document is required.")
        if structural_run is not None and structural_run.id != semantic_run.structural_processing_run_id:
            raise ValueError("Semantic enrichment must belong to the supplied structural run.")
        structural_run_id = semantic_run.structural_processing_run_id
    else:
        if structural_run is None or document.id != structural_run.document_id or structural_run.status != "COMPLETED":
            raise ValueError("A completed structural run for this document is required.")
        structural_run_id = structural_run.id
    if route.model != "text-embedding-3-small":
        raise ValueError("TASK-013 schema supports the configured text-embedding-3-small 1536-dimensional route.")
    route_version = f"{route.provider}:{route.model}"
    identity = [
        ContentIndexRun.document_id == document.id,
        ContentIndexRun.structural_processing_run_id == structural_run_id,
        ContentIndexRun.block_schema_version == block_schema_version,
        ContentIndexRun.embedding_route_version == route_version,
        ContentIndexRun.settings_version == settings_version,
    ]
    identity.append(ContentIndexRun.semantic_processing_run_id == semantic_run.id if semantic_run is not None else ContentIndexRun.semantic_processing_run_id.is_(None))
    run = session.execute(select(ContentIndexRun).where(*identity).limit(1)).scalar_one_or_none()
    if run is not None and run.status == "COMPLETED":
        return run
    if run is None:
        run = ContentIndexRun(document_id=document.id, structural_processing_run_id=structural_run_id, semantic_processing_run_id=semantic_run.id if semantic_run is not None else None, block_schema_version=block_schema_version, embedding_route_version=route_version, embedding_dimensions=1536, settings_version=settings_version)
        session.add(run); session.flush()
    else:
        session.execute(delete(IndexedContentBlock).where(IndexedContentBlock.index_run_id == run.id)); run.status = "PENDING"; run.failure_detail = None
    try:
        candidates = _semantic_candidates(session, semantic_run) if semantic_run is not None else _structural_candidates(session, document=document, structural_run_id=structural_run_id)
        if not candidates:
            raise ValueError("Semantic run produced no indexable content blocks." if semantic_run is not None else "Structural run produced no indexable content blocks.")
        result = gateway.execute(
            ModelTask.EMBEDDING,
            {"input": [candidate["text"] for candidate in candidates], "dimensions": 1536},
            lineage=AIExecutionLineage(
                operation="content_index_embedding",
                operation_id=uuid5(NAMESPACE_URL, f"content-index-run:{run.id}"),
                document_id=document.id,
                semantic_processing_run_id=semantic_run.id if semantic_run is not None else None,
                content_index_run_id=run.id,
            ),
        )
        vectors = result.output.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(candidates) or any(not isinstance(vector, list) or len(vector) != 1536 for vector in vectors): raise ValueError("Embedding provider returned unexpected vector dimensions.")
        for candidate, vector in zip(candidates, vectors, strict=True):
            block_fields = {key: value for key, value in candidate.items() if key != "sources"}
            block = IndexedContentBlock(index_run_id=run.id, document_id=document.id, embedding=vector, search_vector=func.to_tsvector("english", candidate["text"]), grade_level=document.grade_level, subject=document.subject, **block_fields)
            session.add(block); session.flush()
            for source_order, source in enumerate(candidate["sources"]):
                session.add(IndexedContentBlockSource(block_id=block.id, source_order=source_order, **source))
    except Exception as error:
        run.status = "FAILED"; run.failure_detail = f"{type(error).__name__}: {error}"[:1000]
        prior = session.execute(select(ContentIndexRun.id).where(ContentIndexRun.document_id == document.id, ContentIndexRun.status == "COMPLETED", ContentIndexRun.id != run.id).limit(1)).scalar_one_or_none()
        document.status = "INDEX_READY" if prior else ("SEMANTIC_READY" if semantic_run is not None else "STRUCTURAL_READY"); session.flush(); return run
    run.status = "COMPLETED"; run.completed_at = datetime.now(UTC); document.status = "INDEX_READY"; session.flush(); return run


def _semantic_metadata(item: ContentSemanticItem, by_id: dict[object, ContentSemanticItem]) -> dict[str, str | None]:
    result = {"unit_key": None, "lesson_key": None, "concept_key": None}
    current: ContentSemanticItem | None = item
    while current is not None:
        if current.semantic_type == "UNIT": result["unit_key"] = current.semantic_key
        elif current.semantic_type == "LESSON": result["lesson_key"] = current.semantic_key
        elif current.semantic_type == "CONCEPT": result["concept_key"] = current.semantic_key
        current = by_id.get(current.parent_id)
    return result


def _semantic_candidates(session: Session, semantic_run: ContentSemanticProcessingRun) -> list[dict[str, object]]:
    semantic_items = session.execute(select(ContentSemanticItem).where(ContentSemanticItem.semantic_processing_run_id == semantic_run.id).order_by(ContentSemanticItem.semantic_key)).scalars().all()
    semantic_by_id = {item.id: item for item in semantic_items}
    sources = session.execute(select(ContentSemanticItemSource, DocumentStructuralItem).join(DocumentStructuralItem, ContentSemanticItemSource.structural_item_id == DocumentStructuralItem.id).where(ContentSemanticItemSource.semantic_item_id.in_(semantic_by_id)).order_by(ContentSemanticItemSource.semantic_item_id, ContentSemanticItemSource.source_order)).all()
    sources_by_semantic: dict[object, list[tuple[ContentSemanticItemSource, DocumentStructuralItem]]] = {}
    for source, structural in sources: sources_by_semantic.setdefault(source.semantic_item_id, []).append((source, structural))
    candidates: list[dict[str, object]] = []
    for item in semantic_items:
        item_sources = sources_by_semantic.get(item.id, [])
        metadata = _semantic_metadata(item, semantic_by_id)
        refined_sources = refine_semantic_sources(item_sources)
        if not refined_sources:
            fallback_content = "\n".join(value for value in (item.title, item.description) if value)
            if not fallback_content:
                continue
            if len(fallback_content) > MAX_BLOCK_CHARS:
                raise ValueError("Semantic fallback content exceeds the configured block limit without structural boundaries.")
            refined_sources = [(fallback_content, item_sources)]
        for part_index, (part, part_sources) in enumerate(refined_sources):
            candidates.append({
                "semantic_item_id": item.id,
                "block_key": f"{item.semantic_key}:part-{part_index}",
                "block_type": "SEMANTIC",
                "semantic_type": item.semantic_type,
                "text": part,
                "attributes": {"parent_semantic_key": item.semantic_key, "part_index": part_index, **metadata},
                **metadata,
                "sources": [
                    {"semantic_item_id": item.id, "structural_item_id": structural.id, "page_number": source.page_number, "source_ref": source.source_ref}
                    for source, structural in part_sources
                ],
            })
    return candidates


def _structural_candidates(session: Session, *, document: ContentDocument, structural_run_id: object) -> list[dict[str, object]]:
    structural_items = session.execute(select(DocumentStructuralItem).where(DocumentStructuralItem.document_id == document.id, DocumentStructuralItem.processing_run_id == structural_run_id).order_by(DocumentStructuralItem.reading_order, DocumentStructuralItem.item_key)).scalars().all()
    candidates: list[dict[str, object]] = []
    for structural in structural_items:
        source_text = "\n".join(value for value in (structural.text, structural.caption_text) if value).strip()
        if not source_text:
            continue
        for part_index, part in enumerate(_refine_structural_text(source_text)):
            candidates.append({
                "semantic_item_id": None,
                "block_key": f"{structural.item_key}:part-{part_index}",
                "block_type": "STRUCTURAL",
                "semantic_type": None,
                "unit_key": None,
                "lesson_key": None,
                "concept_key": None,
                "text": part,
                "attributes": {
                    "structural_item_key": structural.item_key,
                    "parent_structural_item_id": str(structural.parent_id) if structural.parent_id is not None else None,
                    "sibling_order": structural.sibling_order,
                    "reading_order": structural.reading_order,
                    "hierarchy_depth": structural.hierarchy_depth,
                    "item_type": structural.item_type,
                    "heading_level": structural.heading_level,
                    "page_number": structural.page_number,
                    "source_ref": structural.source_ref,
                    "provenance": structural.provenance,
                    "structural_attributes": structural.attributes,
                    "part_index": part_index,
                },
                "sources": [{"semantic_item_id": None, "structural_item_id": structural.id, "page_number": structural.page_number, "source_ref": structural.source_ref}],
            })
    return candidates


def _refine_structural_text(source_text: str, *, maximum_characters: int = MAX_BLOCK_CHARS) -> list[str]:
    """Retain an individual structural boundary unless it exceeds the block limit."""
    return [source_text[start:start + maximum_characters] for start in range(0, len(source_text), maximum_characters)]


def refine_semantic_sources(
    item_sources: list[tuple[ContentSemanticItemSource, DocumentStructuralItem]],
    *,
    maximum_characters: int = MAX_BLOCK_CHARS,
) -> list[tuple[str, list[tuple[ContentSemanticItemSource, DocumentStructuralItem]]]]:
    """Keep a semantic entity whole where possible, refining only at source boundaries.

    Character slicing is reserved for one structural source that is itself too large.
    """
    blocks: list[tuple[str, list[tuple[ContentSemanticItemSource, DocumentStructuralItem]]]] = []
    current_parts: list[str] = []
    current_sources: list[tuple[ContentSemanticItemSource, DocumentStructuralItem]] = []

    def flush() -> None:
        if current_parts:
            blocks.append(("\n".join(current_parts), list(current_sources)))
            current_parts.clear()
            current_sources.clear()

    for source, structural in item_sources:
        source_text = "\n".join(value for value in (structural.text, structural.caption_text) if value).strip()
        if not source_text:
            continue
        if len(source_text) > maximum_characters:
            flush()
            for start in range(0, len(source_text), maximum_characters):
                blocks.append((source_text[start:start + maximum_characters], [(source, structural)]))
            continue
        if current_parts and len("\n".join([*current_parts, source_text])) > maximum_characters:
            flush()
        current_parts.append(source_text)
        current_sources.append((source, structural))
    flush()
    return blocks


def lexical_candidates(session: Session, *, index_run_id: object, query: str, grade_level: int, subject: str, concept_key: str | None = None, limit: int = 20):
    statement = select(IndexedContentBlock).where(IndexedContentBlock.index_run_id == index_run_id, IndexedContentBlock.grade_level == grade_level, IndexedContentBlock.subject == subject, IndexedContentBlock.search_vector.op("@@")(func.plainto_tsquery("english", query)))
    if concept_key: statement = statement.where(IndexedContentBlock.concept_key == concept_key)
    return session.execute(statement.order_by(func.ts_rank_cd(IndexedContentBlock.search_vector, func.plainto_tsquery("english", query)).desc()).limit(limit)).scalars().all()


def vector_candidates(session: Session, *, index_run_id: object, embedding: list[float], grade_level: int, subject: str, concept_key: str | None = None, limit: int = 20):
    statement = select(IndexedContentBlock).where(IndexedContentBlock.index_run_id == index_run_id, IndexedContentBlock.grade_level == grade_level, IndexedContentBlock.subject == subject)
    if concept_key: statement = statement.where(IndexedContentBlock.concept_key == concept_key)
    return session.execute(statement.order_by(IndexedContentBlock.embedding.cosine_distance(embedding)).limit(limit)).scalars().all()
