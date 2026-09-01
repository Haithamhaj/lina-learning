"""On-demand deterministic Personal Memory Document projection."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import PersonalFact

_GROUPS = {
    "PREFERENCE": "Preferences",
    "FAVORITE": "Favorites",
    "ACTIVITY": "Activities",
    "PET": "Pets",
    "RELATIONSHIP": "Relationships",
    "SAFE_PERSONAL_CONTEXT": "Other Safe Personal Context",
}


def build_personal_memory_document(session: Session, *, student_id: UUID) -> dict[str, object]:
    """Return only the latest value per fact key, with historical count for audit."""

    facts = list(session.scalars(
        select(PersonalFact)
        .where(PersonalFact.student_id == student_id)
        .order_by(PersonalFact.fact_key, PersonalFact.last_observed_at.desc(), PersonalFact.id.desc())
    ))
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    seen: set[str] = set()
    for fact in facts:
        if fact.fact_key in seen:
            continue
        seen.add(fact.fact_key)
        groups[_GROUPS[fact.category]].append({
            "fact_key": fact.fact_key,
            "value": fact.value,
            "display_statement": fact.display_statement,
            "support_count": fact.support_count,
            "last_observed_at": fact.last_observed_at.isoformat(),
        })
    document: dict[str, object] = {group: groups[group] for group in _GROUPS.values() if groups[group]}
    document["historical_fact_count"] = len(facts)
    return document


def format_current_personal_memory_card(session: Session, *, student_id: UUID) -> str | None:
    """Render the full compact current projection for the optional Tutor context."""

    document = build_personal_memory_document(session, student_id=student_id)
    sections: list[str] = []
    for group in _GROUPS.values():
        entries = document.get(group)
        if not isinstance(entries, list) or not entries:
            continue
        statements = [
            entry.get("display_statement")
            for entry in entries
            if isinstance(entry, dict) and isinstance(entry.get("display_statement"), str)
        ]
        if statements:
            sections.append(f"{group}:\n" + "\n".join(f"- {statement}" for statement in statements))
    return "\n\n".join(sections) or None
