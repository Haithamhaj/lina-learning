"""Project-owned hierarchical and hybrid retrieval over the TASK-013 index."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.db.models import (
    ContentDocument,
    ContentIndexRun,
    IndexedContentBlock,
    IndexedContentBlockSource,
    ModelTask,
)


@dataclass(frozen=True)
class CurrentFocus:
    """Optional recent conversational topic context, never curriculum authority."""

    unit_key: str | None = None
    lesson_key: str | None = None
    concept_key: str | None = None


class QueryEmbeddingState(str, Enum):
    NOT_SUPPLIED = "NOT_SUPPLIED"
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class QueryEmbedding:
    """Typed handoff that prevents a failed shared embedding from being retried."""

    state: QueryEmbeddingState
    vector: list[float] | None = None

    @classmethod
    def not_supplied(cls) -> "QueryEmbedding":
        return cls(QueryEmbeddingState.NOT_SUPPLIED)

    @classmethod
    def available(cls, vector: list[float]) -> "QueryEmbedding":
        if len(vector) != 1536 or not all(isinstance(value, (float, int)) for value in vector):
            raise ValueError("Query embedding must contain exactly 1536 numeric dimensions.")
        return cls(QueryEmbeddingState.AVAILABLE, [float(value) for value in vector])

    @classmethod
    def unavailable(cls) -> "QueryEmbedding":
        return cls(QueryEmbeddingState.UNAVAILABLE)

    @property
    def allows_generation(self) -> bool:
        return self.state is QueryEmbeddingState.NOT_SUPPLIED


@dataclass(frozen=True)
class RetrievedBlock:
    text: str
    source_ref: str
    page_number: int | None
    block_type: str
    score: float
    semantic_key: str
    semantic_type: str | None
    concept_key: str | None
    source_refs: tuple[str, ...]
    page_numbers: tuple[int | None, ...]
    matched: bool


@dataclass(frozen=True)
class RetrievalDebug:
    lexical_block_ids: tuple[UUID, ...]
    vector_block_ids: tuple[UUID, ...]
    fused_block_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class RetrievalContext:
    index_run_id: UUID
    blocks: list[RetrievedBlock]
    debug: RetrievalDebug


def reciprocal_rank_fusion(
    lexical_ids: list[UUID | str],
    vector_ids: list[UUID | str],
    *,
    preferred_ids: set[UUID | str] | None = None,
    offset: int = 60,
) -> list[UUID | str]:
    """Fuse two bounded DB-ranked lists without treating scores as comparable."""
    scores: dict[UUID | str, float] = {}
    first_seen: dict[UUID | str, int] = {}
    for source_order, candidates in enumerate((lexical_ids, vector_ids)):
        for rank, identifier in enumerate(candidates, start=1):
            scores[identifier] = scores.get(identifier, 0.0) + 1.0 / (offset + rank)
            first_seen.setdefault(identifier, source_order * len(candidates) + rank)
    preferred = preferred_ids or set()
    return sorted(
        scores,
        key=lambda identifier: (
            -scores[identifier],
            # Current Focus is an advisory preference. It resolves an equally
            # relevant rank, but never lets stale focus outrank the current
            # question's lexical/vector evidence.
            0 if identifier in preferred else 1,
            first_seen[identifier],
            str(identifier),
        ),
    )


class RetrievalService:
    """Retrieve a bounded, source-linked curriculum slice from PostgreSQL."""

    def __init__(
        self, session: Session, *, embedding_gateway: ModelGateway | None = None
    ) -> None:
        self._session = session
        self._embedding_gateway = embedding_gateway

    def retrieve(
        self,
        *,
        student_id: UUID,
        question: str,
        grade_level: int = 5,
        subject: str = "MATH",
        focus: CurrentFocus | None = None,
        limit: int = 4,
        character_budget: int = 2400,
        query_embedding: QueryEmbedding = QueryEmbedding.not_supplied(),
    ) -> list[RetrievedBlock]:
        """Compatibility convenience returning only the selected context blocks."""
        return self.retrieve_with_debug(
            student_id=student_id,
            question=question,
            grade_level=grade_level,
            subject=subject,
            focus=focus,
            block_limit=limit,
            character_budget=character_budget,
            query_embedding=query_embedding,
        ).blocks

    def retrieve_with_debug(
        self,
        *,
        student_id: UUID,
        question: str,
        grade_level: int = 5,
        subject: str = "MATH",
        focus: CurrentFocus | None = None,
        candidate_limit: int = 20,
        block_limit: int = 4,
        character_budget: int = 2400,
        query_embedding: QueryEmbedding = QueryEmbedding.not_supplied(),
    ) -> RetrievalContext:
        if not question.strip():
            raise ValueError("A retrieval question is required.")
        if candidate_limit <= 0 or block_limit <= 0 or character_budget <= 0:
            raise ValueError("Retrieval limits must be positive.")
        index_run_id = self._latest_index_run(
            student_id=student_id, grade_level=grade_level, subject=subject
        )
        if index_run_id is None:
            return RetrievalContext(UUID(int=0), [], RetrievalDebug((), (), ()))
        semantic_types = _semantic_type_hints(question)
        vector = (
            query_embedding.vector
            if query_embedding.state is QueryEmbeddingState.AVAILABLE
            else self._query_embedding(question, student_id=student_id)
            if query_embedding.allows_generation
            else None
        )
        lexical_ids = self._lexical_candidate_ids(
            index_run_id=index_run_id,
            question=question,
            grade_level=grade_level,
            subject=subject,
            focus=None,
            limit=candidate_limit,
        )
        vector_ids = self._vector_candidate_ids(
            index_run_id=index_run_id,
            embedding=vector,
            grade_level=grade_level,
            subject=subject,
            focus=None,
            limit=candidate_limit,
        )
        semantic_preferred_ids = self._semantic_hint_preferred_ids(
            index_run_id=index_run_id,
            candidate_ids=set(lexical_ids).union(vector_ids),
            semantic_types=semantic_types,
        )
        focused_ids: set[UUID] = set()
        if focus is not None:
            focused_ids.update(
                self._lexical_candidate_ids(
                    index_run_id=index_run_id,
                    question=question,
                    grade_level=grade_level,
                    subject=subject,
                    focus=focus,
                    limit=candidate_limit,
                )
            )
            focused_ids.update(
                self._vector_candidate_ids(
                    index_run_id=index_run_id,
                    embedding=vector,
                    grade_level=grade_level,
                    subject=subject,
                    focus=focus,
                    limit=candidate_limit,
                )
            )
        fused_ids = reciprocal_rank_fusion(
            lexical_ids,
            vector_ids,
            preferred_ids=semantic_preferred_ids.union(focused_ids),
        )
        direct_blocks = self._blocks_by_rank(fused_ids)
        expanded_blocks = self._semantic_expansion(
            index_run_id=index_run_id,
            direct_blocks=direct_blocks,
            maximum_blocks=block_limit,
        )
        selected = self._assemble_context(
            [*direct_blocks, *expanded_blocks],
            direct_ids=set(fused_ids),
            block_limit=block_limit,
            character_budget=character_budget,
        )
        return RetrievalContext(
            index_run_id,
            selected,
            RetrievalDebug(tuple(lexical_ids), tuple(vector_ids), tuple(fused_ids)),
        )

    def _latest_index_run(
        self, *, student_id: UUID, grade_level: int, subject: str
    ) -> UUID | None:
        return self._session.execute(
            select(ContentIndexRun.id)
            .join(ContentDocument, ContentDocument.id == ContentIndexRun.document_id)
            .where(
                ContentDocument.student_id == student_id,
                ContentDocument.grade_level == grade_level,
                ContentDocument.subject == subject,
                ContentIndexRun.status == "COMPLETED",
            )
            .order_by(
                ContentIndexRun.completed_at.desc(), ContentIndexRun.created_at.desc()
            )
            .limit(1)
        ).scalar_one_or_none()

    def _filtered_blocks(
        self,
        *,
        index_run_id: UUID,
        grade_level: int,
        subject: str,
        focus: CurrentFocus | None,
    ):
        statement = select(IndexedContentBlock).where(
            IndexedContentBlock.index_run_id == index_run_id,
            IndexedContentBlock.grade_level == grade_level,
            IndexedContentBlock.subject == subject,
        )
        if focus is not None:
            if focus.unit_key is not None:
                statement = statement.where(
                    IndexedContentBlock.unit_key == focus.unit_key
                )
            if focus.lesson_key is not None:
                statement = statement.where(
                    IndexedContentBlock.lesson_key == focus.lesson_key
                )
            if focus.concept_key is not None:
                statement = statement.where(
                    IndexedContentBlock.concept_key == focus.concept_key
                )
        return statement

    def _semantic_hint_preferred_ids(
        self,
        *,
        index_run_id: UUID,
        candidate_ids: set[UUID],
        semantic_types: tuple[str, ...],
    ) -> set[UUID]:
        """Prefer already-relevant enriched blocks without excluding structural ones."""
        if not candidate_ids or not semantic_types:
            return set()
        return set(
            self._session.execute(
                select(IndexedContentBlock.id).where(
                    IndexedContentBlock.index_run_id == index_run_id,
                    IndexedContentBlock.id.in_(candidate_ids),
                    IndexedContentBlock.semantic_type.in_(semantic_types),
                )
            ).scalars()
        )

    def _lexical_candidate_ids(self, **filters: object) -> list[UUID]:
        question = str(filters.pop("question"))
        limit = int(filters.pop("limit"))
        statement = self._filtered_blocks(**filters)  # type: ignore[arg-type]
        query = _lexical_query(question)
        return list(
            self._session.execute(
                statement.where(IndexedContentBlock.search_vector.op("@@")(query))
                .order_by(
                    func.ts_rank_cd(IndexedContentBlock.search_vector, query).desc(),
                    IndexedContentBlock.id,
                )
                .with_only_columns(IndexedContentBlock.id)
                .limit(limit)
            ).scalars()
        )

    def _vector_candidate_ids(
        self, *, embedding: list[float] | None, **filters: object
    ) -> list[UUID]:
        if embedding is None:
            return []
        limit = int(filters.pop("limit"))
        statement = self._filtered_blocks(**filters)  # type: ignore[arg-type]
        return list(
            self._session.execute(
                statement.order_by(
                    IndexedContentBlock.embedding.cosine_distance(embedding),
                    IndexedContentBlock.id,
                )
                .with_only_columns(IndexedContentBlock.id)
                .limit(limit)
            ).scalars()
        )

    def _query_embedding(self, question: str, *, student_id: UUID) -> list[float] | None:
        if self._embedding_gateway is None:
            return None
        result = self._embedding_gateway.execute(
            ModelTask.EMBEDDING,
            {"input": [question], "dimensions": 1536},
            lineage=AIExecutionLineage(
                operation="runtime_retrieval_embedding",
                student_id=student_id,
            ),
        )
        embeddings = result.output.get("embeddings")
        if (
            not isinstance(embeddings, list)
            or len(embeddings) != 1
            or not isinstance(embeddings[0], list)
            or len(embeddings[0]) != 1536
        ):
            raise ValueError(
                "Embedding gateway returned an unexpected query embedding."
            )
        return embeddings[0]

    def _blocks_by_rank(
        self, identifiers: list[UUID | str]
    ) -> list[IndexedContentBlock]:
        ids = [identifier for identifier in identifiers if isinstance(identifier, UUID)]
        if not ids:
            return []
        by_id = {
            block.id: block
            for block in self._session.execute(
                select(IndexedContentBlock).where(IndexedContentBlock.id.in_(ids))
            ).scalars()
        }
        return [by_id[identifier] for identifier in ids if identifier in by_id]

    def _semantic_expansion(
        self,
        *,
        index_run_id: UUID,
        direct_blocks: list[IndexedContentBlock],
        maximum_blocks: int,
    ) -> list[IndexedContentBlock]:
        semantic_item_ids = [
            block.semantic_item_id
            for block in direct_blocks
            if block.semantic_item_id is not None
        ]
        if not semantic_item_ids:
            return []
        direct_ids = [block.id for block in direct_blocks]
        return list(
            self._session.execute(
                select(IndexedContentBlock)
                .where(
                    IndexedContentBlock.index_run_id == index_run_id,
                    IndexedContentBlock.semantic_item_id.in_(semantic_item_ids),
                    IndexedContentBlock.id.not_in(direct_ids),
                )
                .order_by(
                    IndexedContentBlock.semantic_item_id, IndexedContentBlock.block_key
                )
                .limit(maximum_blocks)
            ).scalars()
        )

    def _assemble_context(
        self,
        blocks: list[IndexedContentBlock],
        *,
        direct_ids: set[UUID | str],
        block_limit: int,
        character_budget: int,
    ) -> list[RetrievedBlock]:
        selected: list[RetrievedBlock] = []
        used_characters = 0
        sources_by_block = self._sources_by_block([block.id for block in blocks])
        for block in blocks:
            if (
                len(selected) >= block_limit
                or used_characters + len(block.text) > character_budget
            ):
                continue
            sources = sources_by_block.get(block.id, [])
            source_refs = tuple(source.source_ref for source in sources)
            page_numbers = tuple(source.page_number for source in sources)
            selected.append(
                RetrievedBlock(
                    text=block.text,
                    source_ref=source_refs[0] if source_refs else "",
                    page_number=page_numbers[0] if page_numbers else None,
                    block_type=block.block_type,
                    score=0.0,
                    semantic_key=str(
                        block.attributes.get("parent_semantic_key", block.block_key)
                    ),
                    semantic_type=block.semantic_type,
                    concept_key=block.concept_key,
                    source_refs=source_refs,
                    page_numbers=page_numbers,
                    matched=block.id in direct_ids,
                )
            )
            used_characters += len(block.text)
        return selected

    def _sources_by_block(
        self, block_ids: list[UUID]
    ) -> dict[UUID, list[IndexedContentBlockSource]]:
        if not block_ids:
            return {}
        result: dict[UUID, list[IndexedContentBlockSource]] = {}
        for source in self._session.execute(
            select(IndexedContentBlockSource)
            .where(IndexedContentBlockSource.block_id.in_(block_ids))
            .order_by(
                IndexedContentBlockSource.block_id,
                IndexedContentBlockSource.source_order,
            )
        ).scalars():
            result.setdefault(source.block_id, []).append(source)
        return result


def _semantic_type_hints(question: str) -> tuple[str, ...]:
    """Use explicit user requests as advisory metadata preferences."""
    words = set(re.findall(r"[a-z]+", question.casefold()))
    if words.intersection({"example", "examples"}):
        return ("EXAMPLE",)
    if words.intersection({"exercise", "exercises", "practice", "problem", "problems"}):
        return ("EXERCISE",)
    if words.intersection({"figure", "picture", "diagram", "chart"}):
        return ("FIGURE", "TABLE")
    if words.intersection({"formula", "equation"}):
        return ("FORMULA",)
    return ()


def _lexical_query(question: str):
    """Build a safe OR query so conversational filler cannot suppress a match."""
    terms = [
        term
        for term in re.findall(r"[a-z0-9]+", question.casefold())
        if term
        not in {
            "a",
            "an",
            "and",
            "are",
            "can",
            "how",
            "i",
            "in",
            "is",
            "me",
            "of",
            "the",
            "these",
            "to",
            "we",
            "what",
        }
        and not (term.isdigit() and len(term) == 1)
    ]
    if not terms:
        terms = ["__no_lexical_terms__"]
    return func.to_tsquery("english", " | ".join(terms))
