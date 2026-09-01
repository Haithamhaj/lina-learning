"""Durable ADD/SUPPORT/NOOP reconciliation for Personal Facts."""

from __future__ import annotations

from collections import Counter
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.personal_facts.extraction import (
    AddNewPersonalFactCandidate,
    PersonalFactsExtractionCandidate,
    SupportExistingFactCandidate,
    normalize_assertion,
)
from services.platform.db.models import LearningMessage, LearningSession, PersonalFact, PersonalFactObservation


def reconcile_candidates(
    session: Session,
    *,
    student_id: UUID,
    learning_session: LearningSession,
    candidates: list[PersonalFactsExtractionCandidate],
) -> dict[str, int]:
    """Append source observations; never overwrite a contrary historical value."""

    results: Counter[str] = Counter(added=0, supported=0, noop=0)
    sources = {
        message.id: message
        for message in session.scalars(
            select(LearningMessage).where(
                LearningMessage.session_id == learning_session.id,
                LearningMessage.role == "student",
            )
        )
    }
    for candidate in candidates:
        fact = _existing_fact(session, student_id=student_id, candidate=candidate)
        new_fact = fact is None
        for assertion in candidate.supporting_assertions:
            source = sources.get(assertion.source_message_id)
            if source is None:
                continue
            if fact is None:
                assert isinstance(candidate, AddNewPersonalFactCandidate)
                fact = PersonalFact(
                    student_id=student_id,
                    category=candidate.category,
                    fact_key=candidate.fact_key,
                    value=candidate.value,
                    display_statement=candidate.display_statement,
                    support_count=0,
                    first_observed_at=source.created_at,
                    last_observed_at=source.created_at,
                )
                session.add(fact)
                session.flush()
            exists = session.execute(
                select(PersonalFactObservation.id).where(
                    PersonalFactObservation.personal_fact_id == fact.id,
                    PersonalFactObservation.source_message_id == source.id,
                )
            ).scalar_one_or_none()
            if exists is not None:
                results["noop"] += 1
                continue
            session.add(PersonalFactObservation(
                personal_fact_id=fact.id,
                student_id=student_id,
                source_message_id=source.id,
                source_session_id=learning_session.id,
                observed_at=source.created_at,
                normalized_assertion=normalize_assertion(assertion.explicit_student_assertion),
            ))
            session.flush()
            _rebuild_rollup(session, fact)
            results["added" if new_fact else "supported"] += 1
            new_fact = False
    session.flush()
    return dict(results)


def _existing_fact(
    session: Session,
    *,
    student_id: UUID,
    candidate: PersonalFactsExtractionCandidate,
) -> PersonalFact | None:
    """Resolve a validated known ID or the exact ADD_NEW identity under a row lock."""

    statement = select(PersonalFact).where(PersonalFact.student_id == student_id)
    if isinstance(candidate, SupportExistingFactCandidate):
        statement = statement.where(PersonalFact.id == candidate.existing_fact_id)
    else:
        statement = statement.where(
            PersonalFact.category == candidate.category,
            PersonalFact.fact_key == candidate.fact_key,
            PersonalFact.value == candidate.value,
        )
    return session.execute(statement.with_for_update()).scalar_one_or_none()


def _rebuild_rollup(session: Session, fact: PersonalFact) -> None:
    """Derive cached Fact totals from immutable Observations after every write."""

    count, first, last = session.execute(
        select(
            func.count(PersonalFactObservation.id),
            func.min(PersonalFactObservation.observed_at),
            func.max(PersonalFactObservation.observed_at),
        ).where(PersonalFactObservation.personal_fact_id == fact.id)
    ).one()
    fact.support_count = int(count)
    assert first is not None and last is not None
    fact.first_observed_at = first
    fact.last_observed_at = last
