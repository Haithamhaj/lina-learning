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
from services.platform.db.models import (
    CurrentLearningState,
    LearnerPattern,
    LearningEvidence,
    LearningEvent,
    LearningMessage,
    LearningSession,
    PatternEvidence,
)
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
_ARABIC_NUMERAL_TRANSLATION = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
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
    states = _active_states(
        session, student_id=student_id, subject=subject, now=effective_now
    )
    patterns = _active_patterns(session, student_id=student_id, subject=subject)
    lineage_texts = _student_lineage_texts(
        session,
        student_id=student_id,
        states=states,
        patterns=patterns,
    )
    candidates = _state_candidates(
        states=states,
        lineage_texts=lineage_texts,
        question_terms=question_terms,
        focus_terms=focus_terms,
    )
    candidates.extend(
        _pattern_candidates(
            patterns=patterns,
            lineage_texts=lineage_texts,
            question_terms=question_terms,
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
            0 if candidate.entry.source_kind == "current_state" else 1,
            0 if candidate.entry.source_kind == "current_state" else candidate.scope_priority,
            candidate.source_priority,
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
    *,
    states: list[CurrentLearningState],
    lineage_texts: dict[tuple[str, UUID], str],
    question_terms: set[str],
    focus_terms: set[str],
) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    for state in states:
        question_match, focus_match = _matches(
            concept_ref=state.concept_ref,
            text=state.detail,
            lineage_text=lineage_texts.get(("state", state.id), ""),
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


def _active_states(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
    now: datetime,
) -> list[CurrentLearningState]:
    return list(session.execute(
        select(CurrentLearningState).where(
            CurrentLearningState.student_id == student_id,
            CurrentLearningState.subject == subject,
            CurrentLearningState.status == "ACTIVE",
            CurrentLearningState.policy_version == CURRENT_STATE_POLICY_VERSION,
            # Preserve deprecated rows for audit, but never grant them runtime authority.
            CurrentLearningState.state_type != "current_school_focus",
            or_(CurrentLearningState.expires_at.is_(None), CurrentLearningState.expires_at > now),
        )
    ).scalars())


def _pattern_candidates(
    *,
    patterns: list[LearnerPattern],
    lineage_texts: dict[tuple[str, UUID], str],
    question_terms: set[str],
    focus_terms: set[str],
) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    for pattern in patterns:
        scope = pattern.scope if isinstance(pattern.scope, dict) else {}
        scope_type = str(scope.get("scope_type") or "concept")
        concept_ref = _scope_concept(scope)
        question_match, focus_match = _matches(
            concept_ref=concept_ref,
            text=f"{pattern.pattern_key} {pattern.detail} {scope.get('context_ref', '')}",
            lineage_text=lineage_texts.get(("pattern", pattern.id), ""),
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


def _active_patterns(
    session: Session,
    *,
    student_id: UUID,
    subject: str,
) -> list[LearnerPattern]:
    rows = session.execute(
        select(LearnerPattern).where(
            LearnerPattern.student_id == student_id,
            LearnerPattern.policy_version == PATTERN_POLICY_VERSION,
            LearnerPattern.status.in_(("ACTIVE", "STABLE")),
        )
    ).scalars()
    patterns: list[LearnerPattern] = []
    for pattern in rows:
        scope = pattern.scope if isinstance(pattern.scope, dict) else {}
        if scope.get("subject") != subject:
            continue
        patterns.append(pattern)
    return patterns


def _student_lineage_texts(
    session: Session,
    *,
    student_id: UUID,
    states: list[CurrentLearningState],
    patterns: list[LearnerPattern],
) -> dict[tuple[str, UUID], str]:
    """Read only prior Student text already linked to authoritative candidate rows."""

    evidence_ids_by_owner = {
        ("state", state.id): _uuid_refs(state.evidence_refs)
        for state in states
    }
    pattern_ids = [pattern.id for pattern in patterns]
    if pattern_ids:
        for pattern_id, evidence_id in session.execute(
            select(PatternEvidence.pattern_id, PatternEvidence.evidence_id).where(
                PatternEvidence.pattern_id.in_(pattern_ids)
            )
        ):
            evidence_ids_by_owner.setdefault(("pattern", pattern_id), set()).add(evidence_id)

    evidence_ids = set().union(*evidence_ids_by_owner.values()) if evidence_ids_by_owner else set()
    if not evidence_ids:
        return {}
    source_ids_by_evidence: dict[UUID, set[UUID]] = {}
    for evidence_id, source_message_id, source_message_ids in session.execute(
        select(
            LearningEvidence.id,
            LearningEvent.source_message_id,
            LearningEvent.source_message_ids,
        )
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .where(LearningEvidence.id.in_(evidence_ids))
    ):
        source_ids = _uuid_refs(source_message_ids)
        if source_message_id is not None:
            source_ids.add(source_message_id)
        source_ids_by_evidence[evidence_id] = source_ids

    source_ids = set().union(*source_ids_by_evidence.values()) if source_ids_by_evidence else set()
    if not source_ids:
        return {}
    student_text_by_id = dict(session.execute(
        select(LearningMessage.id, LearningMessage.content)
        .join(LearningSession, LearningMessage.session_id == LearningSession.id)
        .where(
            LearningMessage.id.in_(source_ids),
            LearningMessage.role == "student",
            LearningSession.student_id == student_id,
        )
    ).all())
    return {
        owner: " ".join(
            student_text_by_id[source_id]
            for evidence_id in owner_evidence_ids
            for source_id in source_ids_by_evidence.get(evidence_id, set())
            if source_id in student_text_by_id
        )
        for owner, owner_evidence_ids in evidence_ids_by_owner.items()
    }


def _uuid_refs(values: object) -> set[UUID]:
    if not isinstance(values, list):
        return set()
    refs: set[UUID] = set()
    for value in values:
        try:
            refs.add(UUID(str(value)))
        except (TypeError, ValueError):
            continue
    return refs


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
    lineage_text: str,
    question_terms: set[str],
    focus_terms: set[str],
) -> tuple[bool, bool]:
    candidate_terms = _terms(f"{concept_ref or ''} {text} {lineage_text}")
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
        for term in re.findall(r"[^\W_]+", value.translate(_ARABIC_NUMERAL_TRANSLATION).casefold(), flags=re.UNICODE)
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
