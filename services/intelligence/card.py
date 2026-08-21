"""Compact, deterministic runtime projection of derived learning intelligence.

The Card is deliberately built on demand.  It is not another source of truth:
the selected Current Learning State and Pattern rows remain authoritative and
their identifiers stay attached to every runtime entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from services.intelligence.current_state import CURRENT_STATE_POLICY_VERSION
from services.intelligence.patterns import PATTERN_POLICY_VERSION
from services.platform.db.models import CurrentLearningState, LearnerPattern
from services.retrieval.service import CurrentFocus


INTELLIGENCE_CARD_SCHEMA_VERSION = "learner-intelligence-card-v1"
INTELLIGENCE_CARD_POLICY_VERSION = "learner-intelligence-card-policy-v1"


@dataclass(frozen=True)
class CardBudget:
    """Conservative, centralized runtime bounds for the on-demand Card."""

    max_entries: int = 6
    max_states: int = 3
    max_patterns: int = 3
    max_characters: int = 600


@dataclass(frozen=True)
class CardEntry:
    source_kind: str
    source_id: UUID
    text: str
    concept_ref: str | None
    scope_type: str
    priority: int
    selection_reason: str


@dataclass(frozen=True)
class CardDebug:
    schema_version: str
    policy_version: str
    selected_source_ids: tuple[UUID, ...]
    selection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class LearnerIntelligenceCardProjection:
    """An inspectable runtime slice; it is intentionally not persisted."""

    schema_version: str
    policy_version: str
    entries: tuple[CardEntry, ...]
    character_budget: int
    debug: CardDebug


@dataclass(frozen=True)
class _Candidate:
    entry: CardEntry
    source_priority: int
    scope_priority: int
    recency: datetime
    question_match: bool
    focus_match: bool


_SCOPE_PRIORITIES = {"concept": 0, "context": 1, "subject": 2, "cross_subject": 3, "global": 4}
_STOP_TERMS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "from", "help", "how", "i", "in",
    "is", "it", "me", "my", "of", "please", "the", "this", "to", "what", "why", "with", "you",
}
_FOCUS_FALLBACK_TURNS = {
    "continue",
    "again",
    "help me",
    "i dont understand",
    "i don t understand",
    "كمل",
    "كملي",
    "تابع",
    "تابعي",
    "مرة ثانية",
    "ساعدني",
    "لا افهم",
    "لا أفهم",
    "ما افهم",
    "ما فهمت",
}


def build_learner_intelligence_card(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
    question: str,
    focus: CurrentFocus | None = None,
    budget: CardBudget = CardBudget(),
    now: datetime | None = None,
) -> LearnerIntelligenceCardProjection:
    """Rank then bound the current question's relevant State/Pattern guidance."""

    _validate_budget(budget)
    effective_now = now or datetime.now(UTC)
    question_terms = _terms(question)
    focus_terms = _focus_terms(focus)
    candidates = _state_candidates(
        session, student_id=student_id, subject=subject, question_terms=question_terms,
        focus_terms=focus_terms, now=effective_now,
    )
    candidates.extend(
        _pattern_candidates(
            session, student_id=student_id, subject=subject, question_terms=question_terms,
            focus_terms=focus_terms,
        )
    )

    # CurrentFocus is useful only for known context-dependent continuations.
    # A substantive but unmatched question must not inherit stale intelligence.
    if any(candidate.question_match for candidate in candidates):
        candidates = [candidate for candidate in candidates if candidate.question_match]
    elif _allows_focus_fallback(question):
        candidates = [candidate for candidate in candidates if candidate.focus_match]
    else:
        candidates = []

    candidates.sort(
        key=lambda candidate: (
            candidate.source_priority,
            candidate.scope_priority,
            -candidate.recency.timestamp(),
            str(candidate.entry.source_id),
        )
    )
    entries = _fit_budget(candidates, budget)
    debug = CardDebug(
        schema_version=INTELLIGENCE_CARD_SCHEMA_VERSION,
        policy_version=INTELLIGENCE_CARD_POLICY_VERSION,
        selected_source_ids=tuple(entry.source_id for entry in entries),
        selection_reasons=tuple(entry.selection_reason for entry in entries),
    )
    return LearnerIntelligenceCardProjection(
        schema_version=INTELLIGENCE_CARD_SCHEMA_VERSION,
        policy_version=INTELLIGENCE_CARD_POLICY_VERSION,
        entries=tuple(entries),
        character_budget=budget.max_characters,
        debug=debug,
    )


def _state_candidates(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
    question_terms: set[str],
    focus_terms: set[str],
    now: datetime,
) -> list[_Candidate]:
    rows = session.execute(
        select(CurrentLearningState).where(
            CurrentLearningState.student_id == student_id,
            CurrentLearningState.subject == subject,
            CurrentLearningState.status == "ACTIVE",
            CurrentLearningState.policy_version == CURRENT_STATE_POLICY_VERSION,
            or_(CurrentLearningState.expires_at.is_(None), CurrentLearningState.expires_at > now),
        )
    ).scalars()
    candidates: list[_Candidate] = []
    for state in rows:
        question_match, focus_match = _matches(
            concept_ref=state.concept_ref,
            text=state.detail,
            question_terms=question_terms,
            focus_terms=focus_terms,
        )
        candidates.append(
            _Candidate(
                entry=CardEntry(
                    source_kind="current_state",
                    source_id=state.id,
                    text=state.detail,
                    concept_ref=state.concept_ref,
                    scope_type="concept",
                    priority=0,
                    selection_reason=_selection_reason(question_match, focus_match),
                ),
                source_priority=0,
                scope_priority=0,
                recency=state.updated_at,
                question_match=question_match,
                focus_match=focus_match,
            )
        )
    return candidates


def _pattern_candidates(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
    question_terms: set[str],
    focus_terms: set[str],
) -> list[_Candidate]:
    rows = session.execute(
        select(LearnerPattern).where(
            LearnerPattern.student_id == student_id,
            LearnerPattern.policy_version == PATTERN_POLICY_VERSION,
            LearnerPattern.status.in_(("ACTIVE", "STABLE")),
        )
    ).scalars()
    candidates: list[_Candidate] = []
    for pattern in rows:
        scope = pattern.scope if isinstance(pattern.scope, dict) else {}
        if scope.get("subject") != subject:
            continue
        scope_type = str(scope.get("scope_type") or "concept")
        concept_ref = _scope_concept(scope)
        question_match, focus_match = _matches(
            concept_ref=concept_ref,
            text=f"{pattern.pattern_key} {pattern.detail} {scope.get('context_ref', '')}",
            question_terms=question_terms,
            focus_terms=focus_terms,
        )
        candidates.append(
            _Candidate(
                entry=CardEntry(
                    source_kind="recent_pattern" if pattern.status == "ACTIVE" else "stable_pattern",
                    source_id=pattern.id,
                    text=pattern.detail,
                    concept_ref=concept_ref,
                    scope_type=scope_type,
                    priority=1 if pattern.status == "ACTIVE" else 2,
                    selection_reason=_selection_reason(question_match, focus_match),
                ),
                source_priority=1 if pattern.status == "ACTIVE" else 2,
                scope_priority=_SCOPE_PRIORITIES.get(scope_type, 5),
                recency=pattern.last_supported_at or pattern.first_detected_at,
                question_match=question_match,
                focus_match=focus_match,
            )
        )
    return candidates


def _fit_budget(candidates: list[_Candidate], budget: CardBudget) -> list[CardEntry]:
    selected: list[CardEntry] = []
    state_count = 0
    pattern_count = 0
    used_characters = 0
    for candidate in candidates:
        entry = candidate.entry
        is_state = entry.source_kind == "current_state"
        if len(selected) >= budget.max_entries:
            break
        if is_state and state_count >= budget.max_states:
            continue
        if not is_state and pattern_count >= budget.max_patterns:
            continue
        if used_characters + len(entry.text) > budget.max_characters:
            continue
        selected.append(entry)
        used_characters += len(entry.text)
        if is_state:
            state_count += 1
        else:
            pattern_count += 1
    return selected


def _matches(
    *,
    concept_ref: str | None,
    text: str,
    question_terms: set[str],
    focus_terms: set[str],
) -> tuple[bool, bool]:
    candidate_terms = _terms(f"{concept_ref or ''} {text}")
    return bool(question_terms.intersection(candidate_terms)), bool(focus_terms.intersection(candidate_terms))


def _scope_concept(scope: dict[str, object]) -> str | None:
    for key in ("concept_ref", "context_ref"):
        value = scope.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _selection_reason(question_match: bool, focus_match: bool) -> str:
    if question_match:
        return "exact_question_concept"
    if focus_match:
        return "focus_fallback"
    return "not_selected"


def _terms(value: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[^\W_]+", value.casefold(), flags=re.UNICODE)
        if len(term) > 1 and term not in _STOP_TERMS
    }


def _focus_terms(focus: CurrentFocus | None) -> set[str]:
    if focus is None:
        return set()
    return _terms(" ".join(value for value in (focus.unit_key, focus.lesson_key, focus.concept_key) if value))


def _allows_focus_fallback(question: str) -> bool:
    normalized = " ".join(re.findall(r"[^\W_]+", question.casefold(), flags=re.UNICODE))
    return normalized in _FOCUS_FALLBACK_TURNS


def _validate_budget(budget: CardBudget) -> None:
    if min(budget.max_entries, budget.max_states, budget.max_patterns, budget.max_characters) <= 0:
        raise ValueError("Intelligence Card budget values must be positive.")
