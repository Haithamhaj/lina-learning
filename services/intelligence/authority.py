"""Selection of complete authoritative Evidence processing runs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.intelligence.segment_reviews import (
    SEGMENT_LEARNING_REVIEW_PROMPT_VERSION,
    SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
    SEGMENT_REVIEW_POLICY_VERSION,
)
from services.platform.db.models import (
    CandidateEvent,
    IntelligenceProcessingRun,
    IntelligenceSessionAuthority,
    LearningEvent,
    LearningEvidence,
    LearningSession,
)


def authoritative_evidence_ids(session: Session, *, student_id: UUID) -> list[UUID]:
    """Return complete explicitly authorized runs plus legacy Candidate selections.

    Explicit Session authority selects every Evidence row in one complete run;
    Candidate lineage is optional there. Legacy Sessions without authority keep
    the previous latest-completed interpretation per immutable Candidate.
    """

    authorities = {
        authority.session_id: authority.evidence_processing_run_id
        for authority in session.execute(
            select(IntelligenceSessionAuthority).where(IntelligenceSessionAuthority.student_id == student_id)
        ).scalars()
    }
    rows = session.execute(
        select(
            LearningEvidence.id,
            LearningEvent,
            CandidateEvent,
            IntelligenceProcessingRun,
            LearningSession,
        )
        .join(LearningEvent, LearningEvidence.event_id == LearningEvent.id)
        .outerjoin(CandidateEvent, LearningEvent.candidate_event_id == CandidateEvent.id)
        .join(IntelligenceProcessingRun, LearningEvent.processing_run_id == IntelligenceProcessingRun.id)
        .join(LearningSession, LearningEvent.session_id == LearningSession.id)
        .where(
            IntelligenceProcessingRun.student_id == student_id,
            IntelligenceProcessingRun.status == "COMPLETED",
            LearningSession.student_id == student_id,
        )
    ).all()
    explicitly_authorized: list[tuple[UUID, LearningEvent]] = []
    selected: dict[UUID, tuple[UUID, LearningEvent, IntelligenceProcessingRun]] = {}
    for evidence_id, event, candidate, run, _learning_session in rows:
        authoritative_run_id = authorities.get(event.session_id)
        if authoritative_run_id is not None:
            if event.processing_run_id == authoritative_run_id:
                explicitly_authorized.append((evidence_id, event))
            continue
        if candidate is None:
            # Candidate-free Evidence is activated only through explicit Session
            # authority; legacy fallback remains Candidate-based by design.
            continue
        prior = selected.get(candidate.id)
        if prior is None or _version_key(run, event) > _version_key(prior[2], prior[1]):
            selected[candidate.id] = (evidence_id, event, run)
    return [
        evidence_id
        for evidence_id, _event in sorted(
            explicitly_authorized
            + [(evidence_id, event) for evidence_id, event, _run in selected.values()],
            key=lambda item: (item[1].session_id, str(item[0])),
        )
    ]


def is_supported_evidence_run_scope(scope: object) -> bool:
    """Recognize compiled legacy and deterministic-finalization Evidence runs."""

    if not isinstance(scope, dict):
        return False
    legacy_schema = scope.get("consolidation_schema_version")
    if isinstance(legacy_schema, str) and legacy_schema.startswith("session-evidence-"):
        return True
    return (
        scope.get("intelligence_pipeline") == "segment-finalization-v1"
        and scope.get("segment_review_schema_version") == SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
        and scope.get("segment_review_prompt_version")
        == SEGMENT_LEARNING_REVIEW_PROMPT_VERSION
        and scope.get("segment_review_rubric_version") == "evidence-rubric-v1"
        and scope.get("segment_review_policy_version") == SEGMENT_REVIEW_POLICY_VERSION
    )


def _version_key(run: IntelligenceProcessingRun, event: LearningEvent) -> tuple[datetime, str, str]:
    return run.created_at, str(run.id), str(event.id)
