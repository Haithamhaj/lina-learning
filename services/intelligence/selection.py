"""Compatibility selector over the TASK-024 compact runtime Card."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from services.intelligence.card import CardBudget, build_learner_intelligence_card
from services.retrieval.service import CurrentFocus


@dataclass(frozen=True)
class RelevantIntelligence:
    source_kind: str
    source_id: UUID
    text: str
    concept_ref: str | None
    priority: int


def select_relevant_intelligence(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
    question: str,
    focus: CurrentFocus | None = None,
    character_budget: int = 600,
) -> list[RelevantIntelligence]:
    """Return the Card's selected guidance without exposing historical rows."""

    card = build_learner_intelligence_card(
        session,
        student_id=student_id,
        subject=subject,
        question=question,
        focus=focus,
        budget=CardBudget(max_characters=character_budget),
    )
    return [
        RelevantIntelligence(
            source_kind=entry.source_kind,
            source_id=entry.source_id,
            text=entry.text,
            concept_ref=entry.concept_ref,
            priority=entry.priority,
        )
        for entry in card.entries
    ]


def select_relevant_intelligence_text(**kwargs: object) -> list[str]:
    """Compatibility view for callers that only need advisory text."""

    return [item.text for item in select_relevant_intelligence(**kwargs)]  # type: ignore[arg-type]
