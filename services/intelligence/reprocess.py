"""Bounded, durable TASK-026 reprocessing request planning and queueing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.intelligence.consolidation import (
    ConsolidationVersion,
    EVIDENCE_RUBRIC_VERSION,
    SESSION_CONSOLIDATION_POLICY_VERSION,
    SESSION_EVIDENCE_PROMPT_VERSION,
    SESSION_EVIDENCE_SCHEMA_VERSION,
    require_supported_consolidation_version,
)
from services.intelligence.current_state import CURRENT_STATE_POLICY_VERSION, require_supported_current_state_policy
from services.intelligence.decisions import DECISION_VIEW_POLICY_VERSION, require_supported_decision_view_policy
from services.intelligence.patterns import PATTERN_POLICY_VERSION, require_supported_pattern_policy
from services.platform.db.models import (
    IntelligenceReprocessRun,
    IntelligenceReprocessSession,
    IntelligenceSessionAuthority,
    IntelligenceProcessingRun,
    Job,
    LearningSession,
)
from services.platform.jobs import enqueue_job


INTELLIGENCE_REPROCESS_JOB = "INTELLIGENCE_REPROCESS"


@dataclass(frozen=True)
class EvidenceVersionSelection:
    """Explicit Evidence interpretation identity; defaults name the supported contract."""

    provider: str
    model: str
    schema_version: str = SESSION_EVIDENCE_SCHEMA_VERSION
    prompt_version: str = SESSION_EVIDENCE_PROMPT_VERSION
    rubric_version: str = EVIDENCE_RUBRIC_VERSION
    consolidation_policy_version: str = SESSION_CONSOLIDATION_POLICY_VERSION

    def __post_init__(self) -> None:
        if not self.provider or not self.model:
            raise ValueError("Evidence provider and model must be explicit for a reprocess request.")


@dataclass(frozen=True)
class IntelligenceReprocessRequest:
    student_id: UUID
    evidence: EvidenceVersionSelection
    subject: str | None = None
    session_ids: tuple[UUID, ...] = ()
    start_at: datetime | None = None
    end_at: datetime | None = None
    current_state_policy_version: str = CURRENT_STATE_POLICY_VERSION
    pattern_policy_version: str = PATTERN_POLICY_VERSION
    decision_policy_version: str = DECISION_VIEW_POLICY_VERSION

    def __post_init__(self) -> None:
        if self.start_at and self.end_at and self.start_at > self.end_at:
            raise ValueError("start_at must not be after end_at.")
        if not self.session_ids and self.start_at is None and self.end_at is None:
            raise ValueError("Reprocessing requires session_ids or a bounded date range.")


@dataclass(frozen=True)
class ReprocessPreview:
    selected_session_ids: tuple[UUID, ...]
    selected_session_count: int
    sessions_with_matching_processing: int
    sessions_needing_processing: int
    version_set: dict[str, object]


@dataclass(frozen=True)
class EnqueuedReprocess:
    job: Job
    reprocess_run: IntelligenceReprocessRun


def preview_intelligence_reprocess(session: Session, *, request: IntelligenceReprocessRequest) -> ReprocessPreview:
    _validate_request_versions(request)
    selected = _selected_sessions(session, request=request)
    matching = _sessions_with_matching_evidence(session, selected=selected, evidence=request.evidence)
    return ReprocessPreview(
        selected_session_ids=tuple(item.id for item in selected),
        selected_session_count=len(selected),
        sessions_with_matching_processing=len(matching),
        sessions_needing_processing=len(selected) - len(matching),
        version_set=_version_set(request),
    )


def enqueue_intelligence_reprocess(session: Session, *, request: IntelligenceReprocessRequest) -> EnqueuedReprocess:
    """Create exactly one durable job/run for one normalized request/version set."""

    _validate_request_versions(request)
    selected = _selected_sessions(session, request=request)
    scope = _scope(request, selected)
    version_set = _version_set(request)
    idempotency_key = _idempotency_key(request.student_id, scope, version_set)
    existing = session.execute(
        select(IntelligenceReprocessRun).where(IntelligenceReprocessRun.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if existing is not None:
        job = session.get(Job, existing.job_id) if existing.job_id is not None else None
        if job is None:
            job = enqueue_job(
                session,
                job_type=INTELLIGENCE_REPROCESS_JOB,
                payload={"reprocess_run_id": str(existing.id), "scope": existing.scope, "version_set": existing.version_set},
                idempotency_key=idempotency_key,
            )
            existing.job_id = job.id
            session.flush()
        return EnqueuedReprocess(job=job, reprocess_run=existing)

    run = IntelligenceReprocessRun(
        student_id=request.student_id,
        idempotency_key=idempotency_key,
        scope=scope,
        version_set=version_set,
    )
    session.add(run)
    session.flush()
    job = enqueue_job(
        session,
        job_type=INTELLIGENCE_REPROCESS_JOB,
        payload={"reprocess_run_id": str(run.id), "scope": scope, "version_set": version_set},
        idempotency_key=idempotency_key,
    )
    run.job_id = job.id
    session.flush()
    return EnqueuedReprocess(job=job, reprocess_run=run)


def process_intelligence_reprocess_session(
    session: Session,
    *,
    reprocess_run_id: UUID,
    session_id: UUID,
    gateway: object,
) -> dict[str, object]:
    """Rebuild one closed session and activate it only after all local outputs succeed."""

    from services.intelligence.consolidation import consolidate_closed_session
    from services.intelligence.current_state import apply_processing_run_current_state
    from services.intelligence.decisions import DecisionViewPolicy, apply_processing_run_decision_views
    from services.intelligence.patterns import PatternPolicy, apply_processing_run_patterns

    reprocess_run = session.get(IntelligenceReprocessRun, reprocess_run_id, with_for_update=True)
    learning_session = session.get(LearningSession, session_id, with_for_update=True)
    if reprocess_run is None or learning_session is None:
        raise LookupError("Reprocess run or selected session does not exist.")
    if learning_session.student_id != reprocess_run.student_id or learning_session.status != "CLOSED":
        raise ValueError("Reprocess session is outside the closed requested student scope.")
    item = session.execute(
        select(IntelligenceReprocessSession)
        .where(
            IntelligenceReprocessSession.reprocess_run_id == reprocess_run.id,
            IntelligenceReprocessSession.session_id == learning_session.id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if item is not None and item.status == "COMPLETED":
        return item.result or {"session_id": str(session_id), "reused": True}
    if item is None:
        item = IntelligenceReprocessSession(reprocess_run_id=reprocess_run.id, session_id=learning_session.id)
        session.add(item)
    item.status = "RUNNING"
    item.started_at = datetime.now(UTC)
    session.flush()
    versions = reprocess_run.version_set
    evidence_versions = versions["evidence"] if isinstance(versions.get("evidence"), dict) else {}
    outcome = consolidate_closed_session(
        session,
        learning_session=learning_session,
        gateway=gateway,  # type: ignore[arg-type]
        version=ConsolidationVersion(
            schema_version=str(evidence_versions.get("schema_version", SESSION_EVIDENCE_SCHEMA_VERSION)),
            prompt_version=str(evidence_versions.get("prompt_version", SESSION_EVIDENCE_PROMPT_VERSION)),
            rubric_version=str(evidence_versions.get("rubric_version", EVIDENCE_RUBRIC_VERSION)),
            policy_version=str(evidence_versions.get("consolidation_policy_version", SESSION_CONSOLIDATION_POLICY_VERSION)),
            provider=evidence_versions.get("provider") if isinstance(evidence_versions.get("provider"), str) else None,
            model=evidence_versions.get("model") if isinstance(evidence_versions.get("model"), str) else None,
        ),
    )
    observed_at = learning_session.closed_at or learning_session.last_activity_at
    states = apply_processing_run_current_state(
        session,
        processing_run_id=outcome.processing_run.id,
        now=observed_at,
        policy_version=str(versions["current_state_policy_version"]),
    )
    patterns = apply_processing_run_patterns(
        session,
        processing_run_id=outcome.processing_run.id,
        now=datetime.now(UTC),
        policy=PatternPolicy(version=str(versions["pattern_policy_version"])),
    )
    decisions = apply_processing_run_decision_views(
        session,
        processing_run_id=outcome.processing_run.id,
        policy=DecisionViewPolicy(version=str(versions["decision_policy_version"])),
    )
    authority = session.execute(
        select(IntelligenceSessionAuthority)
        .where(
            IntelligenceSessionAuthority.student_id == reprocess_run.student_id,
            IntelligenceSessionAuthority.session_id == learning_session.id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if authority is None:
        authority = IntelligenceSessionAuthority(
            student_id=reprocess_run.student_id,
            session_id=learning_session.id,
            reprocess_run_id=reprocess_run.id,
            evidence_processing_run_id=outcome.processing_run.id,
        )
        session.add(authority)
    else:
        authority.reprocess_run_id = reprocess_run.id
        authority.evidence_processing_run_id = outcome.processing_run.id
        authority.activated_at = datetime.now(UTC)
    result = {
        "session_id": str(learning_session.id),
        "processing_run_id": str(outcome.processing_run.id),
        "event_count": outcome.event_count,
        "current_state_count": len(states),
        "pattern_count": len(patterns),
        "decision_view_count": len(decisions),
    }
    item.evidence_processing_run_id = outcome.processing_run.id
    item.status = "COMPLETED"
    item.completed_at = datetime.now(UTC)
    item.result = result
    item.error = None
    session.flush()
    return result


def record_reprocess_session_failure(
    session: Session,
    *,
    reprocess_run_id: UUID,
    session_id: UUID,
    error: Exception,
) -> dict[str, str]:
    """Durably retain a failed session without activating any interpretation."""

    item = session.execute(
        select(IntelligenceReprocessSession)
        .where(
            IntelligenceReprocessSession.reprocess_run_id == reprocess_run_id,
            IntelligenceReprocessSession.session_id == session_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if item is None:
        item = IntelligenceReprocessSession(reprocess_run_id=reprocess_run_id, session_id=session_id)
        session.add(item)
    message = f"{type(error).__name__}: {error}"
    item.status = "FAILED"
    item.error = message[:1000]
    item.completed_at = datetime.now(UTC)
    session.flush()
    return {"session_id": str(session_id), "error": item.error}


def _selected_sessions(session: Session, *, request: IntelligenceReprocessRequest) -> list[LearningSession]:
    query = select(LearningSession).where(
        LearningSession.student_id == request.student_id,
        LearningSession.status == "CLOSED",
    )
    if request.subject is not None:
        query = query.where(LearningSession.subject == request.subject)
    if request.session_ids:
        query = query.where(LearningSession.id.in_(request.session_ids))
    if request.start_at is not None:
        query = query.where(LearningSession.closed_at >= request.start_at)
    if request.end_at is not None:
        query = query.where(LearningSession.closed_at <= request.end_at)
    return list(session.execute(query.order_by(LearningSession.closed_at, LearningSession.id)).scalars())


def _scope(request: IntelligenceReprocessRequest, selected: list[LearningSession]) -> dict[str, object]:
    return {
        "student_id": str(request.student_id),
        "subject": request.subject,
        "session_ids": [str(item.id) for item in selected],
        "start_at": request.start_at.isoformat() if request.start_at else None,
        "end_at": request.end_at.isoformat() if request.end_at else None,
    }


def _sessions_with_matching_evidence(
    session: Session,
    *,
    selected: list[LearningSession],
    evidence: EvidenceVersionSelection,
) -> set[UUID]:
    session_ids = {item.id for item in selected}
    if not session_ids:
        return set()
    rows = session.execute(
        select(IntelligenceProcessingRun.scope).where(
            IntelligenceProcessingRun.status == "COMPLETED",
            IntelligenceProcessingRun.rubric_version == evidence.rubric_version,
            IntelligenceProcessingRun.policy_version == evidence.consolidation_policy_version,
            IntelligenceProcessingRun.scope["session_id"].astext.in_([str(item) for item in session_ids]),
            IntelligenceProcessingRun.scope["consolidation_schema_version"].astext == evidence.schema_version,
            IntelligenceProcessingRun.scope["prompt_version"].astext == evidence.prompt_version,
        )
    ).scalars()
    matched: set[UUID] = set()
    for scope in rows:
        if not isinstance(scope, dict):
            continue
        if evidence.provider is not None and scope.get("provider") != evidence.provider:
            continue
        if evidence.model is not None and scope.get("model") != evidence.model:
            continue
        raw_session_id = scope.get("session_id")
        if isinstance(raw_session_id, str):
            matched.add(UUID(raw_session_id))
    return matched


def _version_set(request: IntelligenceReprocessRequest) -> dict[str, object]:
    return {
        "evidence": asdict(request.evidence),
        "current_state_policy_version": request.current_state_policy_version,
        "pattern_policy_version": request.pattern_policy_version,
        "decision_policy_version": request.decision_policy_version,
    }


def _validate_request_versions(request: IntelligenceReprocessRequest) -> None:
    require_supported_current_state_policy(request.current_state_policy_version)
    require_supported_pattern_policy(request.pattern_policy_version)
    require_supported_decision_view_policy(request.decision_policy_version)
    require_supported_consolidation_version(
        ConsolidationVersion(
            schema_version=request.evidence.schema_version,
            prompt_version=request.evidence.prompt_version,
            rubric_version=request.evidence.rubric_version,
            policy_version=request.evidence.consolidation_policy_version,
            provider=request.evidence.provider,
            model=request.evidence.model,
        )
    )


def _idempotency_key(student_id: UUID, scope: dict[str, object], version_set: dict[str, object]) -> str:
    encoded = json.dumps({"student_id": str(student_id), "scope": scope, "version_set": version_set}, sort_keys=True, separators=(",", ":"))
    return f"intelligence-reprocess:{sha256(encoded.encode()).hexdigest()}"
