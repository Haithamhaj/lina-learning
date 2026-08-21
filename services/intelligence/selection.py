"""Deterministic runtime selection of relevant learner intelligence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import CurrentLearningState, LearnerPattern
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
    """Select active, question-relevant guidance without loading a full profile."""

    if character_budget <= 0:
        raise ValueError("Intelligence budget must be positive.")
    terms = _terms(question, focus)
    selected: list[RelevantIntelligence] = []
    for state in session.execute(
        select(CurrentLearningState).where(
            CurrentLearningState.student_id == student_id,
            CurrentLearningState.status == "ACTIVE",
        )
    ).scalars():
        if _is_relevant(state.concept_ref, state.detail, terms, focus):
            selected.append(
                RelevantIntelligence(
                    source_kind="current_state",
                    source_id=state.id,
                    text=state.detail,
                    concept_ref=state.concept_ref,
                    priority=0,
                )
            )
    for pattern in session.execute(
        select(LearnerPattern).where(
            LearnerPattern.student_id == student_id,
            LearnerPattern.status.in_(("ACTIVE", "STABLE", "WEAKENING")),
        )
    ).scalars():
        pattern_subject = pattern.scope.get("subject") if isinstance(pattern.scope, dict) else None
        if pattern_subject != subject or not _is_relevant(
            str(pattern.scope.get("concept_ref") or "") if isinstance(pattern.scope, dict) else None,
            f"{pattern.pattern_key} {pattern.detail}",
            terms,
            focus,
        ):
            continue
        selected.append(
            RelevantIntelligence(
                source_kind="recent_pattern" if pattern.status != "STABLE" else "stable_pattern",
                source_id=pattern.id,
                text=pattern.detail,
                concept_ref=str(pattern.scope.get("concept_ref")) if isinstance(pattern.scope, dict) and pattern.scope.get("concept_ref") else None,
                priority=1 if pattern.status != "STABLE" else 2,
            )
        )
    selected.sort(key=lambda item: (item.priority, str(item.source_id)))
    result: list[RelevantIntelligence] = []
    used = 0
    for item in selected:
        if used + len(item.text) > character_budget:
            continue
        result.append(item)
        used += len(item.text)
    return result


def select_relevant_intelligence_text(**kwargs: object) -> list[str]:
    """Compatibility view for callers that only need advisory text."""

    return [item.text for item in select_relevant_intelligence(**kwargs)]  # type: ignore[arg-type]


def _terms(question: str, focus: CurrentFocus | None) -> set[str]:
    terms = set(re.findall(r"[a-z0-9]+", question.casefold()))
    if focus is not None:
        for value in (focus.unit_key, focus.lesson_key, focus.concept_key):
            if value:
                terms.update(re.findall(r"[a-z0-9]+", value.casefold()))
    return {term for term in terms if len(term) > 1}


def _is_relevant(
    concept_ref: str | None,
    text: str,
    terms: set[str],
    focus: CurrentFocus | None,
) -> bool:
    if focus is not None and concept_ref and concept_ref == focus.concept_key:
        return True
    haystack = set(re.findall(r"[a-z0-9]+", f"{concept_ref or ''} {text}".casefold()))
    return bool(terms.intersection(haystack))
