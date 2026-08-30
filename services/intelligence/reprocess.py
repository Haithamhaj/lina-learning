"""Bounded, durable TASK-026 reprocessing request planning and queueing."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.intelligence.consolidation import (
    EVIDENCE_RUBRIC_VERSION,
    SESSION_CONSOLIDATION_POLICY_VERSION,
    SESSION_EVIDENCE_PROMPT_VERSION,
    SESSION_EVIDENCE_SCHEMA_VERSION,
    ConsolidationVersion,
    EvidenceContractError,
    require_supported_consolidation_version,
)
from services.intelligence.current_state import (
    CURRENT_STATE_POLICY_VERSION,
    require_supported_current_state_policy,
)
from services.intelligence.decisions import (
    DECISION_VIEW_POLICY_VERSION,
    require_supported_decision_view_policy,
)
from services.intelligence.patterns import (
    PATTERN_POLICY_VERSION,
    require_supported_pattern_policy,
)
from services.intelligence.segment_reviews import (
    SEGMENT_LEARNING_REVIEW_PROMPT_VERSION,
    SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
    SEGMENT_REVIEW_POLICY_VERSION,
)
from services.model_gateway.gateway import ModelGateway
from services.platform.config import Settings
from services.platform.db.models import (
    IntelligenceProcessingRun,
    IntelligenceReprocessRun,
    IntelligenceReprocessSession,
    IntelligenceSessionAuthority,
    Job,
    LearningSession,
)
from services.platform.jobs import enqueue_job
from services.tutor.session_lifecycle import (
    LEGACY_SESSION_EVIDENCE_PIPELINE,
    SESSION_FINALIZATION_PIPELINE,
)

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
class SegmentReviewVersionSelection:
    """Semantic identity for finalization-backed reprocessing.

    Provider and model are deliberately excluded: they describe execution
    lineage, not whether a persisted strict Review satisfies this contract.
    """

    schema_version: str = SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
    prompt_version: str = SEGMENT_LEARNING_REVIEW_PROMPT_VERSION
    rubric_version: str = EVIDENCE_RUBRIC_VERSION
    review_policy_version: str = SEGMENT_REVIEW_POLICY_VERSION
    finalization_pipeline: str = SESSION_FINALIZATION_PIPELINE


@dataclass(frozen=True)
class IntelligenceReprocessRequest:
    student_id: UUID
    evidence: EvidenceVersionSelection
    segment_review: SegmentReviewVersionSelection = field(default_factory=SegmentReviewVersionSelection)
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
    segment_evidence_gateway: ModelGateway | None = None,
    segment_review_settings: Settings | None = None,
) -> dict[str, object]:
    """Stage one closed session's Evidence interpretation for scope-level activation."""

    from services.intelligence.consolidation import consolidate_closed_session
    from services.intelligence.session_finalization import (
        stage_closed_session_finalization,
    )

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
    if learning_session.intelligence_pipeline == SESSION_FINALIZATION_PIPELINE:
        outcome = stage_closed_session_finalization(
            session,
            learning_session=learning_session,
            review_gateway=segment_evidence_gateway,
            review_settings=segment_review_settings,
        )
    elif learning_session.intelligence_pipeline == LEGACY_SESSION_EVIDENCE_PIPELINE:
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
    else:
        raise ValueError("Unsupported Session intelligence pipeline for reprocessing.")
    result = {
        "session_id": str(learning_session.id),
        "processing_run_id": str(outcome.processing_run.id),
        "event_count": outcome.event_count,
        "staged": True,
    }
    item.evidence_processing_run_id = outcome.processing_run.id
    item.status = "COMPLETED"
    item.completed_at = datetime.now(UTC)
    item.result = result
    item.error = None
    session.flush()
    return result


def activate_reprocess_scope(
    session: Session,
    *,
    reprocess_run_id: UUID,
) -> dict[str, object]:
    """Atomically make a fully staged reprocess scope authoritative.

    Evidence is rebuilt per session, but State, Pattern, and Decision derivation is
    deliberately deferred until every selected session has completed.  This keeps
    all runtime-visible intelligence on one coherent authority generation.
    """

    from services.intelligence.current_state import rebuild_authoritative_current_states
    from services.intelligence.decisions import (
        DecisionViewPolicy,
        rebuild_authoritative_decision_views,
    )
    from services.intelligence.patterns import (
        PatternPolicy,
        rebuild_authoritative_patterns,
    )

    reprocess_run = session.get(IntelligenceReprocessRun, reprocess_run_id, with_for_update=True)
    if reprocess_run is None:
        raise LookupError(f"Reprocess run {reprocess_run_id!r} does not exist.")
    existing_result = reprocess_run.result if isinstance(reprocess_run.result, dict) else {}
    existing_activation = existing_result.get("activation")
    if isinstance(existing_activation, dict) and existing_activation.get("status") == "COMPLETED":
        return existing_activation

    raw_session_ids = reprocess_run.scope.get("session_ids", []) if isinstance(reprocess_run.scope, dict) else []
    selected_session_ids = tuple(UUID(str(value)) for value in raw_session_ids)
    if not selected_session_ids:
        raise ValueError("Reprocess activation requires a non-empty selected session scope.")
    items = list(
        session.execute(
            select(IntelligenceReprocessSession)
            .where(
                IntelligenceReprocessSession.reprocess_run_id == reprocess_run.id,
                IntelligenceReprocessSession.session_id.in_(selected_session_ids),
            )
            .with_for_update()
        ).scalars()
    )
    items_by_session = {item.session_id: item for item in items}
    if set(items_by_session) != set(selected_session_ids) or any(
        item.status != "COMPLETED" or item.evidence_processing_run_id is None
        for item in items_by_session.values()
    ):
        raise ValueError("Reprocess scope cannot activate until every selected session has completed.")

    versions = reprocess_run.version_set
    _validate_staged_session_runs(
        session,
        reprocess_run=reprocess_run,
        items_by_session=items_by_session,
        selected_session_ids=selected_session_ids,
        versions=versions,
    )
    existing_authorities = {
        authority.session_id: authority
        for authority in session.execute(
            select(IntelligenceSessionAuthority)
            .where(
                IntelligenceSessionAuthority.student_id == reprocess_run.student_id,
                IntelligenceSessionAuthority.session_id.in_(selected_session_ids),
            )
            .with_for_update()
        ).scalars()
    }
    activated_at = datetime.now(UTC)
    previous_authority_by_session: dict[str, dict[str, str | None]] = {}
    new_evidence_runs_by_session: dict[str, str] = {}
    for session_id in selected_session_ids:
        previous = existing_authorities.get(session_id)
        previous_authority_by_session[str(session_id)] = {
            "reprocess_run_id": str(previous.reprocess_run_id) if previous is not None else None,
            "evidence_processing_run_id": str(previous.evidence_processing_run_id) if previous is not None else None,
        }
        item = items_by_session[session_id]
        assert item.evidence_processing_run_id is not None
        new_evidence_runs_by_session[str(session_id)] = str(item.evidence_processing_run_id)
        if previous is None:
            session.add(
                IntelligenceSessionAuthority(
                    student_id=reprocess_run.student_id,
                    session_id=session_id,
                    reprocess_run_id=reprocess_run.id,
                    evidence_processing_run_id=item.evidence_processing_run_id,
                    activated_at=activated_at,
                )
            )
        else:
            previous.reprocess_run_id = reprocess_run.id
            previous.evidence_processing_run_id = item.evidence_processing_run_id
            previous.activated_at = activated_at
    session.flush()

    states = rebuild_authoritative_current_states(
        session,
        student_id=reprocess_run.student_id,
        now=activated_at,
        policy_version=str(versions["current_state_policy_version"]),
    )
    patterns = rebuild_authoritative_patterns(
        session,
        student_id=reprocess_run.student_id,
        now=activated_at,
        policy=PatternPolicy(version=str(versions["pattern_policy_version"])),
    )
    first_item = items_by_session[selected_session_ids[0]]
    assert first_item.evidence_processing_run_id is not None
    decisions = rebuild_authoritative_decision_views(
        session,
        student_id=reprocess_run.student_id,
        processing_run_id=first_item.evidence_processing_run_id,
        policy=DecisionViewPolicy(version=str(versions["decision_policy_version"])),
        now=activated_at,
    )

    return {
        "status": "COMPLETED",
        "reprocess_run_id": str(reprocess_run.id),
        "selected_session_ids": [str(session_id) for session_id in selected_session_ids],
        "previous_authority_by_session": previous_authority_by_session,
        "new_evidence_processing_runs_by_session": new_evidence_runs_by_session,
        "activated_at": activated_at.isoformat(),
        "version_identity": versions,
        "current_state_count": len(states),
        "pattern_count": len(patterns),
        "decision_view_count": len(decisions),
    }


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
    session_ids = {
        item.id
        for item in selected
        if item.intelligence_pipeline == LEGACY_SESSION_EVIDENCE_PIPELINE
    }
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
        "segment_review": asdict(request.segment_review),
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
    if (
        request.segment_review.schema_version != SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
        or request.segment_review.prompt_version != SEGMENT_LEARNING_REVIEW_PROMPT_VERSION
        or request.segment_review.rubric_version != EVIDENCE_RUBRIC_VERSION
        or request.segment_review.review_policy_version != SEGMENT_REVIEW_POLICY_VERSION
        or request.segment_review.finalization_pipeline != SESSION_FINALIZATION_PIPELINE
    ):
        raise EvidenceContractError("Segment Review interpretation version is not supported.")


def _validate_staged_session_runs(
    session: Session,
    *,
    reprocess_run: IntelligenceReprocessRun,
    items_by_session: dict[UUID, IntelligenceReprocessSession],
    selected_session_ids: tuple[UUID, ...],
    versions: dict[str, object],
) -> None:
    """Prove each staged generation belongs to the selected pipeline and Session.

    This runs before any authority mutation so a stale job or manually malformed
    staging artifact cannot transiently point a live Session at the wrong run.
    """

    selected_sessions = {
        learning_session.id: learning_session
        for learning_session in session.scalars(
            select(LearningSession)
            .where(LearningSession.id.in_(selected_session_ids))
            .with_for_update()
        )
    }
    if set(selected_sessions) != set(selected_session_ids):
        raise ValueError("Reprocess activation selected Session lineage is incomplete.")
    evidence_versions = versions.get("evidence") if isinstance(versions.get("evidence"), dict) else {}
    review_versions = versions.get("segment_review") if isinstance(versions.get("segment_review"), dict) else {}
    for session_id in selected_session_ids:
        learning_session = selected_sessions[session_id]
        item = items_by_session[session_id]
        assert item.evidence_processing_run_id is not None
        staged_run = session.get(
            IntelligenceProcessingRun,
            item.evidence_processing_run_id,
            with_for_update=True,
        )
        scope = staged_run.scope if staged_run is not None and isinstance(staged_run.scope, dict) else {}
        if (
            staged_run is None
            or staged_run.status != "COMPLETED"
            or staged_run.student_id != reprocess_run.student_id
            or learning_session.student_id != reprocess_run.student_id
            or learning_session.status != "CLOSED"
            or scope.get("session_id") != str(session_id)
            or (
                learning_session.intelligence_pipeline == SESSION_FINALIZATION_PIPELINE
                and scope.get("intelligence_pipeline") != SESSION_FINALIZATION_PIPELINE
            )
            or (
                learning_session.intelligence_pipeline == LEGACY_SESSION_EVIDENCE_PIPELINE
                and scope.get("intelligence_pipeline") not in (None, LEGACY_SESSION_EVIDENCE_PIPELINE)
            )
        ):
            raise ValueError("Reprocess staged processing run does not match the selected Session lineage.")
        if learning_session.intelligence_pipeline == SESSION_FINALIZATION_PIPELINE:
            if (
                staged_run.rubric_version != str(review_versions.get("rubric_version"))
                or staged_run.policy_version != str(review_versions.get("review_policy_version"))
                or scope.get("intelligence_pipeline") != review_versions.get("finalization_pipeline")
                or scope.get("segment_review_schema_version") != review_versions.get("schema_version")
                or scope.get("segment_review_prompt_version") != review_versions.get("prompt_version")
                or scope.get("segment_review_rubric_version") != review_versions.get("rubric_version")
                or scope.get("segment_review_policy_version") != review_versions.get("review_policy_version")
            ):
                raise ValueError("Reprocess staged Segment Review contract does not match the request.")
        elif learning_session.intelligence_pipeline == LEGACY_SESSION_EVIDENCE_PIPELINE:
            if (
                staged_run.rubric_version != str(evidence_versions.get("rubric_version"))
                or staged_run.policy_version != str(evidence_versions.get("consolidation_policy_version"))
                or scope.get("consolidation_schema_version") != evidence_versions.get("schema_version")
                or scope.get("prompt_version") != evidence_versions.get("prompt_version")
            ):
                raise ValueError("Reprocess staged legacy Evidence contract does not match the request.")
        else:
            raise ValueError("Reprocess staged Session uses an unsupported intelligence pipeline.")


def _idempotency_key(student_id: UUID, scope: dict[str, object], version_set: dict[str, object]) -> str:
    encoded = json.dumps({"student_id": str(student_id), "scope": scope, "version_set": version_set}, sort_keys=True, separators=(",", ":"))
    return f"intelligence-reprocess:{sha256(encoded.encode()).hexdigest()}"
