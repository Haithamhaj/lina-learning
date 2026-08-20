"""Project-owned, provenance-first hybrid retrieval for the Math vertical slice."""

from __future__ import annotations

from dataclasses import dataclass
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import ContentBlock, ContentDocument

from .embeddings import deterministic_embedding


@dataclass(frozen=True)
class RetrievedBlock:
    text: str
    source_ref: str
    page_number: int | None
    block_type: str
    score: float


class RetrievalService:
    """Keep filtering, ranking, budgets, and provenance in the Lina domain."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def retrieve(
        self,
        *,
        student_id: UUID,
        question: str,
        grade_level: int = 5,
        subject: str = "MATH",
        limit: int = 4,
        character_budget: int = 2400,
    ) -> list[RetrievedBlock]:
        terms = set(re.findall(r"[a-z0-9]+", question.lower()))
        query_embedding = deterministic_embedding(question)
        rows = self._session.execute(
            select(ContentBlock, ContentDocument)
            .join(ContentDocument, ContentBlock.document_id == ContentDocument.id)
            .where(
                ContentDocument.student_id == student_id,
                ContentDocument.grade_level == grade_level,
                ContentDocument.subject == subject,
                ContentDocument.status == "STRUCTURAL_READY",
            )
        ).all()
        ranked: list[RetrievedBlock] = []
        for block, _ in rows:
            block_terms = set(re.findall(r"[a-z0-9]+", block.text.lower()))
            lexical = len(terms & block_terms)
            embedding = block.embedding if block.embedding is not None else []
            vector = sum(a * b for a, b in zip(query_embedding, embedding))
            score = lexical * 10 + vector
            if lexical or vector > 0.2:
                ranked.append(RetrievedBlock(block.text, block.source_ref, block.page_number, block.block_type, score))
        selected: list[RetrievedBlock] = []
        used = 0
        for item in sorted(ranked, key=lambda value: value.score, reverse=True):
            if len(selected) >= limit or used + len(item.text) > character_budget:
                continue
            selected.append(item)
            used += len(item.text)
        return selected
