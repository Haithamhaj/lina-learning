"""Explicit persistence helpers for source and derived content."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import (
    ContentBlock,
    ContentDocument,
    ContentProcessingRun,
    ContentSemanticItem,
    ContentSemanticItemSource,
    ContentSemanticProcessingRun,
    DocumentStructuralItem,
)

from .semantic_contract import SemanticExtractionItem
from .structural_contract import NormalizedStructuralItem


def create_content_document(
    session: Session,
    *,
    student_id: UUID,
    grade_level: int,
    subject: str,
    original_storage_key: str,
    original_checksum: str,
    filename: str,
    content_type: str,
) -> ContentDocument:
    document = ContentDocument(
        student_id=student_id,
        grade_level=grade_level,
        subject=subject,
        original_storage_key=original_storage_key,
        original_checksum=original_checksum,
        filename=filename,
        content_type=content_type,
    )
    session.add(document)
    session.flush()
    return document


def create_processing_run(
    session: Session,
    *,
    document_id: UUID,
    kind: str,
    processor_version: str,
    processor_name: str = "unknown",
    library_version: str | None = None,
    processor_settings_version: str = "legacy-unspecified",
    processor_metadata: dict[str, object] | None = None,
) -> ContentProcessingRun:
    run = ContentProcessingRun(
        document_id=document_id,
        kind=kind,
        processor_name=processor_name,
        processor_version=processor_version,
        library_version=library_version,
        processor_settings_version=processor_settings_version,
        processor_metadata=processor_metadata or {},
    )
    session.add(run)
    session.flush()
    return run


def find_processing_run(
    session: Session,
    *,
    document_id: UUID,
    kind: str,
    processor_version: str,
    processor_settings_version: str = "legacy-unspecified",
) -> ContentProcessingRun | None:
    """Return the single idempotent derivation run for an input/version pair."""

    return session.execute(
        select(ContentProcessingRun).where(
            ContentProcessingRun.document_id == document_id,
            ContentProcessingRun.kind == kind,
            ContentProcessingRun.processor_version == processor_version,
            ContentProcessingRun.processor_settings_version == processor_settings_version,
        )
    ).scalar_one_or_none()


def create_content_block(
    session: Session,
    *,
    document_id: UUID,
    processing_run_id: UUID,
    text: str,
    block_type: str,
    page_number: int | None,
    source_ref: str,
    attributes: dict[str, object] | None = None,
) -> ContentBlock:
    block = ContentBlock(
        document_id=document_id,
        processing_run_id=processing_run_id,
        text=text,
        block_type=block_type,
        page_number=page_number,
        source_ref=source_ref,
        attributes=attributes or {},
    )
    session.add(block)
    session.flush()
    return block


def create_structural_items(
    session: Session,
    *,
    document_id: UUID,
    processing_run_id: UUID,
    items: list[NormalizedStructuralItem],
) -> list[DocumentStructuralItem]:
    """Persist a normalized tree in two passes so parent IDs remain queryable."""

    persisted_by_key: dict[str, DocumentStructuralItem] = {}
    for item in items:
        if item.item_key in persisted_by_key:
            raise ValueError(f"Duplicate structural item key {item.item_key!r}.")
        persisted = DocumentStructuralItem(
            document_id=document_id,
            processing_run_id=processing_run_id,
            item_key=item.item_key,
            sibling_order=item.sibling_order,
            reading_order=item.reading_order,
            hierarchy_depth=item.hierarchy_depth,
            item_type=item.item_type,
            text=item.text,
            caption_text=item.caption_text,
            caption_item_keys=list(item.caption_item_keys),
            heading_level=item.heading_level,
            page_number=item.page_number,
            source_ref=item.source_ref,
            provenance=item.provenance,
            attributes=item.attributes,
        )
        session.add(persisted)
        persisted_by_key[item.item_key] = persisted
    session.flush()
    for item in items:
        if item.parent_item_key is None:
            continue
        parent = persisted_by_key.get(item.parent_item_key)
        if parent is None:
            raise ValueError(
                f"Structural item {item.item_key!r} references missing parent {item.parent_item_key!r}."
            )
        persisted_by_key[item.item_key].parent_id = parent.id
    session.flush()
    return [persisted_by_key[item.item_key] for item in items]


def create_semantic_processing_run(
    session: Session,
    *,
    document_id: UUID,
    structural_processing_run_id: UUID,
    semantic_schema_version: str,
    prompt_version: str,
    model_route_version: str,
    provider: str,
    model: str,
    settings_version: str,
    settings_metadata: dict[str, object],
) -> ContentSemanticProcessingRun:
    run = ContentSemanticProcessingRun(
        document_id=document_id,
        structural_processing_run_id=structural_processing_run_id,
        semantic_schema_version=semantic_schema_version,
        prompt_version=prompt_version,
        model_route_version=model_route_version,
        provider=provider,
        model=model,
        settings_version=settings_version,
        settings_metadata=settings_metadata,
    )
    session.add(run)
    session.flush()
    return run


def find_semantic_processing_run(
    session: Session,
    *,
    document_id: UUID,
    structural_processing_run_id: UUID,
    semantic_schema_version: str,
    prompt_version: str,
    model_route_version: str,
    settings_version: str,
) -> ContentSemanticProcessingRun | None:
    return session.execute(
        select(ContentSemanticProcessingRun)
        .where(
            ContentSemanticProcessingRun.document_id == document_id,
            ContentSemanticProcessingRun.structural_processing_run_id == structural_processing_run_id,
            ContentSemanticProcessingRun.semantic_schema_version == semantic_schema_version,
            ContentSemanticProcessingRun.prompt_version == prompt_version,
            ContentSemanticProcessingRun.model_route_version == model_route_version,
            ContentSemanticProcessingRun.settings_version == settings_version,
        )
        .limit(1)
    ).scalar_one_or_none()


def create_semantic_items(
    session: Session,
    *,
    document_id: UUID,
    semantic_processing_run_id: UUID,
    items: list[SemanticExtractionItem],
    structural_items_by_key: dict[str, DocumentStructuralItem],
) -> list[ContentSemanticItem]:
    """Persist an already validated semantic tree and its exact source links."""

    persisted_by_key: dict[str, ContentSemanticItem] = {}
    for item in items:
        persisted = ContentSemanticItem(
            document_id=document_id,
            semantic_processing_run_id=semantic_processing_run_id,
            semantic_key=item.semantic_key,
            semantic_type=item.semantic_type,
            title=item.title,
            normalized_concept_key=item.normalized_concept_key,
            description=item.description,
            sibling_order=item.sibling_order,
            attributes=item.metadata,
        )
        session.add(persisted)
        persisted_by_key[item.semantic_key] = persisted
    session.flush()
    for item in items:
        if item.parent_semantic_key is not None:
            persisted_by_key[item.semantic_key].parent_id = persisted_by_key[item.parent_semantic_key].id
        for source_order, structural_key in enumerate(item.structural_item_keys):
            structural_item = structural_items_by_key[structural_key]
            session.add(
                ContentSemanticItemSource(
                    semantic_item_id=persisted_by_key[item.semantic_key].id,
                    structural_item_id=structural_item.id,
                    structural_item_key=structural_item.item_key,
                    page_number=structural_item.page_number,
                    source_ref=structural_item.source_ref,
                    source_order=source_order,
                )
            )
    session.flush()
    return [persisted_by_key[item.semantic_key] for item in items]
