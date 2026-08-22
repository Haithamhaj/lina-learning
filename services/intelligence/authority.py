"""Selection of the one authoritative Evidence interpretation per raw Candidate."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import (
    CandidateEvent,
    IntelligenceProcessingRun,
    IntelligenceSessionAuthority,
    LearningEvidence,
    LearningEvent,
)


def authoritative_evidence_ids(session: Session, *, student_id: UUID) -> list[UUID]:
    """Return one completed Evidence interpretation for each immutable Candidate.

    Session authority is explicit when present.  Legacy sessions without an
    authority row retain the existing latest-completed-interpretation behavior.
    """

    authorities = {
        authority.session_id: authority.evidence_processing_run_id
        for authority in session.execute(
            select(IntelligenceSessionAuthority).where(IntelligenceSessionAuthority.student_id == student_id)
        ).scalars()
    }
    rows = session.execute(
        select(LearningEvidence.id, LearningEvent, CandidateEvent, IntelligenceProcessingRun)
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .join(CandidateEvent, LearningEvent.candidate_event_id == CandidateEvent.id)
        .join(IntelligenceProcessingRun, LearningEvent.processing_run_id == IntelligenceProcessingRun.id)
        .where(
            IntelligenceProcessingRun.student_id == student_id,
            IntelligenceProcessingRun.status == "COMPLETED",
        )
    ).all()
    selected: dict[UUID, tuple[UUID, LearningEvent, IntelligenceProcessingRun]] = {}
    for evidence_id, event, candidate, run in rows:
        authoritative_run_id = authorities.get(event.session_id)
        if authoritative_run_id is not None and event.processing_run_id != authoritative_run_id:
            continue
        prior = selected.get(candidate.id)
        if prior is None or _version_key(run, event) > _version_key(prior[2], prior[1]):
            selected[candidate.id] = (evidence_id, event, run)
    return [
        evidence_id
        for evidence_id, event, _ in sorted(
            selected.values(),
            key=lambda item: (item[1].session_id, str(item[0])),
        )
    ]


def _version_key(run: IntelligenceProcessingRun, event: LearningEvent) -> tuple[datetime, str, str]:
    return run.created_at, str(run.id), str(event.id)
