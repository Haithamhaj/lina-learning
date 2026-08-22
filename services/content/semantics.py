"""Versioned Grade 5 Math semantic extraction from project-owned structure."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.db.models import (
    ContentDocument,
    ContentProcessingRun,
    ContentSemanticItem,
    ContentSemanticProcessingRun,
    DocumentStructuralItem,
    ModelTask,
)

from .repository import (
    create_semantic_items,
    create_semantic_processing_run,
    find_semantic_processing_run,
)
from .semantic_contract import (
    SEMANTIC_SCHEMA_VERSION,
    SemanticContractError,
    SemanticExtractionItem,
    parse_semantic_output,
    validate_semantic_output,
)


SEMANTIC_PROMPT_VERSION = "grade5-math-semantics-prompt-v4"
SEMANTIC_SETTINGS_VERSION = "hierarchy-aware-coherent-batches-v2"
DEFAULT_MAX_STRUCTURAL_ITEMS_PER_BATCH = 24

_SHARED_INSTRUCTIONS = """You identify educational meaning in a Grade 5 Math workbook.
Use only the supplied normalized structural items and known semantic context.
Return only one JSON object with schema_version
"grade5-math-semantic-schema-v1", items, and
unclassified_structural_item_keys. Each item must use exactly one of UNIT,
LESSON, CONCEPT, OBJECTIVE, DEFINITION, EXPLANATION, EXAMPLE, EXERCISE,
VOCABULARY, FIGURE, TABLE, or FORMULA. Use structural_item_keys only from the
explicit batch allowed_structural_item_keys list; identifiers not in that list
are invalid. Every emitted semantic item MUST contain at least one
allowed_structural_item_key from its current batch. known_semantic_context and
continuation_context are reference-only, never source evidence: do not cite
their structural items. Do not re-emit an existing Unit, Lesson, or Concept
merely to preserve hierarchy. A new item under known context should reference
parent_semantic_key while citing its own current-batch structural source. Every
structural item in this batch must be either linked to one or more semantic
items or listed in unclassified_structural_item_keys. Do not invent source
references, pages, or semantic parents. Educational classification is required
only where the source supports it; decorative or irrelevant items may remain unclassified. When a
source presents a module/document identity and a coherent instructional or
practice section, represent those as UNIT and LESSON rather than leaving that
curriculum grouping unclassified. Put the Lesson under its Unit. When an
instruction states what the learner should demonstrate, capture that goal as
an OBJECTIVE as well as any related exercise. When a relevant structural
picture, table, or formula supports a concept or exercise, emit its FIGURE,
TABLE, or FORMULA reference instead of leaving it unclassified. Keep titles,
descriptions, and metadata compact; omit unnecessary optional detail."""


@dataclass(frozen=True)
class SemanticBatchPlan:
    """One deterministic source-only semantic batch and non-citable context."""

    structural_items: tuple[DocumentStructuralItem, ...]
    continuation_parent_items: tuple[DocumentStructuralItem, ...] = ()


def extract_educational_semantics(
    session: Session,
    *,
    document: ContentDocument,
    structural_run: ContentProcessingRun,
    gateway: ModelGateway,
    semantic_schema_version: str = SEMANTIC_SCHEMA_VERSION,
    prompt_version: str = SEMANTIC_PROMPT_VERSION,
    settings_version: str = SEMANTIC_SETTINGS_VERSION,
    max_structural_items_per_batch: int = DEFAULT_MAX_STRUCTURAL_ITEMS_PER_BATCH,
) -> ContentSemanticProcessingRun:
    """Create a validated semantic derivation without mutating structural truth.

    Input is deterministically planned in reading order. Later batches receive
    only compact Unit/Lesson/Concept references, never raw history.
    """

    if document.grade_level != 5 or document.subject.upper() != "MATH":
        raise ValueError("Educational semantic extraction is limited to Grade 5 Math documents.")
    if max_structural_items_per_batch < 1:
        raise ValueError("max_structural_items_per_batch must be positive.")

    locked_document = session.execute(
        select(ContentDocument).where(ContentDocument.id == document.id).with_for_update()
    ).scalar_one()
    if structural_run.document_id != locked_document.id or structural_run.kind != "STRUCTURAL":
        raise ValueError("Semantic extraction requires the document's structural processing run.")
    if structural_run.status != "COMPLETED":
        raise ValueError("Semantic extraction requires a completed structural processing run.")

    route = gateway.route_for(ModelTask.CURRICULUM_SEMANTICS)
    model_route_version = f"{route.provider}:{route.model}"
    run = find_semantic_processing_run(
        session,
        document_id=locked_document.id,
        structural_processing_run_id=structural_run.id,
        semantic_schema_version=semantic_schema_version,
        prompt_version=prompt_version,
        model_route_version=model_route_version,
        settings_version=settings_version,
    )
    if run is not None and run.status == "COMPLETED":
        return run
    if run is None:
        run = create_semantic_processing_run(
            session,
            document_id=locked_document.id,
            structural_processing_run_id=structural_run.id,
            semantic_schema_version=semantic_schema_version,
            prompt_version=prompt_version,
            model_route_version=model_route_version,
            provider=route.provider,
            model=route.model,
            settings_version=settings_version,
            settings_metadata={
                "batching": "hierarchy-aware-coherent-batches",
                "max_structural_items_per_batch": max_structural_items_per_batch,
                "source_contract": "document-structural-items-v1",
            },
        )
    else:
        session.execute(
            delete(ContentSemanticItem).where(ContentSemanticItem.semantic_processing_run_id == run.id)
        )
        run.status = "PENDING"
        run.failure_detail = None

    structural_items = session.execute(
        select(DocumentStructuralItem)
        .where(DocumentStructuralItem.processing_run_id == structural_run.id)
        .order_by(DocumentStructuralItem.reading_order, DocumentStructuralItem.item_key)
    ).scalars().all()
    if not structural_items:
        return _record_failure(
            session,
            document=locked_document,
            run=run,
            error=ValueError("Structural processing run has no persisted items."),
        )

    locked_document.status = "SEMANTIC_PROCESSING"
    parent_key_by_id = {item.id: item.item_key for item in structural_items}
    all_items: list[SemanticExtractionItem] = []
    known_parent_keys: set[str] = set()
    try:
        for batch_index, plan in enumerate(
            _plan_semantic_batches(structural_items, max_items=max_structural_items_per_batch)
        ):
            batch = list(plan.structural_items)
            output = _extract_batch(
                gateway,
                semantic_run=run,
                document=locked_document,
                batch=batch,
                batch_index=batch_index,
                parent_key_by_id=parent_key_by_id,
                known_items=[item for item in all_items if item.semantic_type in {"UNIT", "LESSON", "CONCEPT"}],
                continuation_parent_items=plan.continuation_parent_items,
            )
            validate_semantic_output(
                output,
                available_structural_item_keys={item.item_key for item in batch},
                allowed_parent_semantic_keys=known_parent_keys,
            )
            duplicate = next(
                (item.semantic_key for item in output.items if item.semantic_key in known_parent_keys),
                None,
            )
            if duplicate is not None:
                raise SemanticContractError(f"Duplicate semantic key across batches {duplicate!r}.")
            all_items.extend(output.items)
            known_parent_keys.update(item.semantic_key for item in output.items)

        _validate_semantic_coverage(structural_items, all_items)
        create_semantic_items(
            session,
            document_id=locked_document.id,
            semantic_processing_run_id=run.id,
            items=all_items,
            structural_items_by_key={item.item_key: item for item in structural_items},
        )
    except Exception as error:
        return _record_failure(session, document=locked_document, run=run, error=error)

    run.status = "COMPLETED"
    run.completed_at = datetime.now(UTC)
    locked_document.status = "SEMANTIC_READY"
    session.flush()
    return run


def _plan_semantic_batches(
    structural_items: list[DocumentStructuralItem], *, max_items: int
) -> list[SemanticBatchPlan]:
    """Plan disjoint, reading-order batches without splitting fitting subtrees.

    The document wrapper is an individual item. Its direct children become the
    outermost planning units, so a synthetic body node cannot make the whole
    workbook one batch. Nested groups appear only in an outer planning unit,
    never in overlapping parent/child units.
    """

    if max_items < 1:
        raise ValueError("max_items must be positive.")

    ordered = sorted(structural_items, key=lambda item: (item.reading_order, item.item_key))
    by_id = {item.id: item for item in ordered}
    children_by_parent: dict[object, list[DocumentStructuralItem]] = {}
    for item in ordered:
        children_by_parent.setdefault(item.parent_id, []).append(item)
    for children in children_by_parent.values():
        children.sort(key=lambda item: (item.reading_order, item.item_key))

    wrapper_ids = {item.id for item in ordered if item.parent_id is None}
    positions = {item.id: index for index, item in enumerate(ordered)}
    assigned: set[object] = set()
    units: list[list[DocumentStructuralItem]] = []

    def subtree(root: DocumentStructuralItem) -> list[DocumentStructuralItem]:
        result = [root]
        for child in children_by_parent.get(root.id, []):
            result.extend(subtree(child))
        return result

    for item in ordered:
        if item.id in assigned:
            continue
        if item.parent_id in wrapper_ids:
            candidate = sorted(subtree(item), key=lambda node: (node.reading_order, node.item_key))
            start = positions[candidate[0].id]
            contiguous = [positions[node.id] for node in candidate] == list(
                range(start, start + len(candidate))
            )
            unit = candidate if contiguous else [item]
        else:
            unit = [item]
        units.append(unit)
        assigned.update(node.id for node in unit)

    plans: list[SemanticBatchPlan] = []
    current: list[DocumentStructuralItem] = []

    def flush_current() -> None:
        nonlocal current
        if current:
            plans.append(SemanticBatchPlan(structural_items=tuple(current)))
            current = []

    def continuation_parents(
        chunk: list[DocumentStructuralItem], unit: list[DocumentStructuralItem]
    ) -> tuple[DocumentStructuralItem, ...]:
        chunk_ids = {item.id for item in chunk}
        unit_ids = {item.id for item in unit}
        parents: list[DocumentStructuralItem] = []
        parent_id = chunk[0].parent_id
        while parent_id in by_id:
            parent = by_id[parent_id]
            if parent.id in unit_ids and parent.id not in chunk_ids:
                parents.append(parent)
            parent_id = parent.parent_id
        return tuple(reversed(parents))

    for unit in units:
        if len(unit) <= max_items:
            if current and len(current) + len(unit) > max_items:
                flush_current()
            current.extend(unit)
            continue

        flush_current()
        for start in range(0, len(unit), max_items):
            chunk = unit[start : start + max_items]
            plans.append(
                SemanticBatchPlan(
                    structural_items=tuple(chunk),
                    continuation_parent_items=continuation_parents(chunk, unit) if start else (),
                )
            )

    flush_current()
    return plans


def _extract_batch(
    gateway: ModelGateway,
    *,
    semantic_run: ContentSemanticProcessingRun,
    document: ContentDocument,
    batch: list[DocumentStructuralItem],
    batch_index: int,
    parent_key_by_id: dict[object, str],
    known_items: list[SemanticExtractionItem],
    continuation_parent_items: Iterable[DocumentStructuralItem] = (),
):
    continuation_items = list(continuation_parent_items)
    payload = {
        "instructions": _SHARED_INSTRUCTIONS,
        "input": json.dumps(
            {
                "schema_version": SEMANTIC_SCHEMA_VERSION,
                "document": {
                    "grade_level": document.grade_level,
                    "subject": document.subject,
                    "filename": document.filename,
                },
                "batch": {
                    "index": batch_index,
                    "allowed_structural_item_keys": [item.item_key for item in batch],
                    "structural_items": [
                        _structural_context_item(item, parent_key_by_id.get(item.parent_id))
                        for item in batch
                    ],
                },
                "continuation_context": {
                    "reference_only": True,
                    "non_citable": True,
                    "parent_structural_items": [
                        _structural_context_item(item, parent_key_by_id.get(item.parent_id))
                        for item in continuation_items
                    ],
                }
                if continuation_items
                else None,
                "known_semantic_context": [
                    {
                        "semantic_key": item.semantic_key,
                        "semantic_type": item.semantic_type,
                        "title": item.title,
                    }
                    for item in known_items
                ],
                "output_schema": {
                    "items": [
                        "semantic_key", "semantic_type", "title", "description",
                        "normalized_concept_key", "parent_semantic_key",
                        "structural_item_keys", "sibling_order", "metadata",
                    ],
                    "unclassified_structural_item_keys": "all remaining batch keys",
                },
            },
            ensure_ascii=False,
        ),
        "max_output_tokens": 3000,
    }
    result = gateway.execute(
        ModelTask.CURRICULUM_SEMANTICS,
        payload,
        lineage=AIExecutionLineage(
            operation="curriculum_semantic_extraction",
            operation_id=uuid5(
                NAMESPACE_URL, f"semantic-processing-run:{semantic_run.id}"
            ),
            document_id=document.id,
            semantic_processing_run_id=semantic_run.id,
        ),
    )
    response_text = result.output.get("text")
    if not isinstance(response_text, str):
        raise SemanticContractError("Semantic model output did not contain text.")
    return parse_semantic_output(response_text)


def _structural_context_item(
    item: DocumentStructuralItem, parent_item_key: str | None
) -> dict[str, object]:
    return {
        "item_key": item.item_key,
        "parent_item_key": parent_item_key,
        "item_type": item.item_type,
        "reading_order": item.reading_order,
        "heading_level": item.heading_level,
        "page_number": item.page_number,
        "source_ref": item.source_ref,
        "text": item.text,
        "caption_text": item.caption_text,
        "attributes": item.attributes,
    }


def _validate_semantic_coverage(
    structural_items: list[DocumentStructuralItem], items: list[SemanticExtractionItem]
) -> None:
    types = {item.semantic_type for item in items}
    heading_count = sum(item.heading_level is not None for item in structural_items)
    if heading_count >= 2 and not {"UNIT", "LESSON"}.issubset(types):
        raise SemanticContractError(
            "Structural hierarchy indicates organized source content, but semantic output has no Unit/Lesson coverage."
        )
    by_key = {item.semantic_key: item for item in items}
    for item in items:
        if item.parent_semantic_key is None:
            continue
        parent = by_key[item.parent_semantic_key]
        if item.semantic_type == "LESSON" and parent.semantic_type != "UNIT":
            raise SemanticContractError("A Lesson must be parented by a Unit.")
        if item.semantic_type in {"CONCEPT", "EXERCISE", "FIGURE", "TABLE", "FORMULA"} and parent.semantic_type not in {"UNIT", "LESSON", "CONCEPT"}:
            raise SemanticContractError(f"{item.semantic_type} has an invalid educational parent.")
        if item.semantic_type in {"OBJECTIVE", "DEFINITION", "EXPLANATION", "EXAMPLE", "VOCABULARY"} and parent.semantic_type not in {"LESSON", "CONCEPT"}:
            raise SemanticContractError(f"{item.semantic_type} has an invalid educational parent.")
    seen_labels: set[tuple[str, str | None, str]] = set()
    for item in items:
        if item.semantic_type not in {"UNIT", "LESSON"}:
            continue
        key = (item.semantic_type, item.parent_semantic_key, item.title.casefold())
        if key in seen_labels:
            raise SemanticContractError(f"Catastrophic duplicate {item.semantic_type.title()} title {item.title!r}.")
        seen_labels.add(key)


def _record_failure(
    session: Session,
    *,
    document: ContentDocument,
    run: ContentSemanticProcessingRun,
    error: Exception,
) -> ContentSemanticProcessingRun:
    run.status = "FAILED"
    run.failure_detail = f"{type(error).__name__}: {error}"[:1000]
    prior_completed_run = session.execute(
        select(ContentSemanticProcessingRun.id)
        .where(
            ContentSemanticProcessingRun.document_id == document.id,
            ContentSemanticProcessingRun.status == "COMPLETED",
            ContentSemanticProcessingRun.id != run.id,
        )
        .limit(1)
    ).scalar_one_or_none()
    document.status = "SEMANTIC_READY" if prior_completed_run is not None else "STRUCTURAL_READY"
    session.flush()
    return run
