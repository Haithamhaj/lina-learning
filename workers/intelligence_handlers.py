"""Worker-owned session consolidation handler."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.consolidation import consolidate_closed_session
from services.intelligence.current_state import apply_processing_run_current_state
from services.intelligence.decisions import apply_processing_run_decision_views
from services.intelligence.patterns import apply_processing_run_patterns
from services.intelligence.session_finalization import finalize_closed_session
from services.model_gateway.factory import create_session_evidence_gateway
from services.model_gateway.factory import create_segment_evidence_gateway
from services.model_gateway.gateway import ModelGateway
from services.platform.db.models import Job, LearningSegment, LearningSession
from services.platform.db.models import IntelligenceReprocessRun
from services.intelligence.reprocess import (
    INTELLIGENCE_REPROCESS_JOB,
    activate_reprocess_scope,
    process_intelligence_reprocess_session,
    record_reprocess_session_failure,
)
from services.tutor.session_lifecycle import (
    LEGACY_SESSION_EVIDENCE_PIPELINE,
    SESSION_CONSOLIDATION_JOB,
    SESSION_FINALIZATION_PIPELINE,
    SESSION_INTELLIGENCE_FINALIZE_JOB,
    enqueue_session_intelligence_finalization_if_ready,
)
from services.tutor.segment_lifecycle import (
    SEGMENT_LEARNING_REVIEW_JOB,
    SEGMENT_REVIEW_REQUEST_VERSION,
)
from services.intelligence.segment_reviews import (
    SegmentReviewLineageError,
    review_completed_segment,
)

if TYPE_CHECKING:
    from workers.job_worker import JobHandlerRegistry


def register_intelligence_handlers(
    registry: "JobHandlerRegistry",
    *,
    session_factory: sessionmaker[Session],
    evidence_gateway_factory: Callable[[Session], ModelGateway] = create_session_evidence_gateway,
    segment_evidence_gateway_factory: Callable[[Session], ModelGateway] | None = None,
) -> None:
    """Register only the approved closed-session evidence job for TASK-021."""

    def handle_consolidation(job: Job) -> dict[str, object]:
        session_id = job.payload.get("session_id")
        if not isinstance(session_id, str):
            raise ValueError("SESSION_CONSOLIDATION requires session_id.")
        with session_factory() as session:
            learning_session = session.get(LearningSession, UUID(session_id), with_for_update=True)
            if learning_session is None:
                raise LookupError(f"Learning session {session_id!r} does not exist.")
            if learning_session.intelligence_pipeline != LEGACY_SESSION_EVIDENCE_PIPELINE:
                raise ValueError(
                    "SESSION_CONSOLIDATION is only valid for legacy-session-evidence-v1 Sessions."
                )
            try:
                outcome = consolidate_closed_session(
                    session,
                    learning_session=learning_session,
                    gateway=evidence_gateway_factory(session),
                )
                states = apply_processing_run_current_state(
                    session,
                    processing_run_id=outcome.processing_run.id,
                )
                patterns = apply_processing_run_patterns(
                    session,
                    processing_run_id=outcome.processing_run.id,
                )
                decision_views = apply_processing_run_decision_views(
                    session,
                    processing_run_id=outcome.processing_run.id,
                )
            except Exception:
                session.commit()
                raise
            session.commit()
            return {
                "session_id": session_id,
                "processing_run_id": str(outcome.processing_run.id),
                "event_count": outcome.event_count,
                "current_state_count": len(states),
                "pattern_count": len(patterns),
                "decision_view_count": len(decision_views),
            }

    registry.register(SESSION_CONSOLIDATION_JOB, handle_consolidation)

    def handle_session_finalization(job: Job) -> dict[str, object]:
        """Activate a complete Segment Review set without any model execution."""

        payload = job.payload if isinstance(job.payload, dict) else {}
        raw_session_id = payload.get("session_id")
        raw_student_id = payload.get("student_id")
        if not isinstance(raw_session_id, str) or not isinstance(raw_student_id, str):
            raise ValueError("SESSION_INTELLIGENCE_FINALIZE requires Session lineage.")
        if payload.get("intelligence_pipeline") != SESSION_FINALIZATION_PIPELINE:
            raise ValueError("Unsupported Session finalization pipeline contract.")
        try:
            session_id = UUID(raw_session_id)
            student_id = UUID(raw_student_id)
        except ValueError as error:
            raise ValueError("SESSION_INTELLIGENCE_FINALIZE has invalid Session lineage.") from error

        with session_factory() as session:
            learning_session = session.get(LearningSession, session_id, with_for_update=True)
            if (
                learning_session is None
                or learning_session.student_id != student_id
                or learning_session.intelligence_pipeline != SESSION_FINALIZATION_PIPELINE
            ):
                raise ValueError("SESSION_INTELLIGENCE_FINALIZE Session lineage does not match.")
            outcome = finalize_closed_session(
                session,
                learning_session=learning_session,
            )
            session.commit()
            return {
                "session_id": raw_session_id,
                "processing_run_id": str(outcome.processing_run.id),
                "event_count": outcome.event_count,
                "evidence_count": outcome.evidence_count,
                "withheld_finding_count": outcome.withheld_finding_count,
                "current_state_count": outcome.current_state_count,
                "pattern_count": outcome.pattern_count,
                "decision_view_count": outcome.decision_view_count,
                "reused": outcome.reused,
            }

    registry.register(SESSION_INTELLIGENCE_FINALIZE_JOB, handle_session_finalization)

    def handle_segment_review(job: Job) -> dict[str, object]:
        """Execute only B's exact staged Segment Review request contract."""

        payload = job.payload if isinstance(job.payload, dict) else {}
        if segment_evidence_gateway_factory is None:
            raise LookupError("Segment Review handler is not configured.")
        if payload.get("review_request_version") != SEGMENT_REVIEW_REQUEST_VERSION:
            raise ValueError("UnsupportedSegmentReviewContract")
        raw_ids = {field: payload.get(field) for field in ("student_id", "session_id", "segment_id")}
        if not all(isinstance(value, str) for value in raw_ids.values()):
            raise ValueError("SegmentReviewLineageError")
        try:
            student_id = UUID(str(raw_ids["student_id"]))
            session_id = UUID(str(raw_ids["session_id"]))
            segment_id = UUID(str(raw_ids["segment_id"]))
        except ValueError as error:
            raise ValueError("SegmentReviewLineageError") from error
        with session_factory() as session:
            learning_session = session.get(LearningSession, session_id, with_for_update=True)
            segment = session.get(LearningSegment, segment_id, with_for_update=True)
            if (
                learning_session is None
                or segment is None
                or learning_session.student_id != student_id
                or segment.session_id != learning_session.id
                or not isinstance(payload.get("closed_at"), str)
                or payload.get("closed_at") != (segment.closed_at.isoformat() if segment.closed_at else None)
                or payload.get("closure_reason") != segment.closure_reason
            ):
                raise SegmentReviewLineageError("SegmentReviewLineageError")
            try:
                outcome = review_completed_segment(
                    session,
                    learning_session=learning_session,
                    segment=segment,
                    gateway=segment_evidence_gateway_factory(session),
                )
                enqueue_session_intelligence_finalization_if_ready(
                    session,
                    learning_session=learning_session,
                )
            except Exception:
                # Preserve the Review's own safe FAILED marker before the Job
                # worker records and retries its separate operational failure.
                session.commit()
                raise
            session.commit()
            return {
                "segment_id": str(segment.id),
                "segment_review_id": str(outcome.review.id),
                "review_status": outcome.review.status,
                "finding_count": outcome.finding_count,
                "model_called": outcome.model_called,
            }

    if segment_evidence_gateway_factory is not None:
        registry.register(SEGMENT_LEARNING_REVIEW_JOB, handle_segment_review)

    def handle_reprocess(job: Job) -> dict[str, object]:
        raw_run_id = job.payload.get("reprocess_run_id")
        if not isinstance(raw_run_id, str):
            raise ValueError("INTELLIGENCE_REPROCESS requires reprocess_run_id.")
        reprocess_run_id = UUID(raw_run_id)
        with session_factory.begin() as session:
            reprocess_run = session.get(IntelligenceReprocessRun, reprocess_run_id, with_for_update=True)
            if reprocess_run is None:
                raise LookupError(f"Reprocess run {raw_run_id!r} does not exist.")
            reprocess_run.status = "RUNNING"
            from datetime import UTC, datetime
            reprocess_run.started_at = reprocess_run.started_at or datetime.now(UTC)
            session_ids = reprocess_run.scope.get("session_ids", []) if isinstance(reprocess_run.scope, dict) else []
        results: list[dict[str, object]] = []
        failures: list[dict[str, str]] = []
        for raw_session_id in session_ids:
            target_session_id = UUID(str(raw_session_id))
            try:
                with session_factory.begin() as session:
                    result = process_intelligence_reprocess_session(
                        session,
                        reprocess_run_id=reprocess_run_id,
                        session_id=target_session_id,
                        gateway=evidence_gateway_factory(session),
                    )
                    results.append(result)
            except Exception as error:
                with session_factory.begin() as session:
                    failures.append(
                        record_reprocess_session_failure(
                            session,
                            reprocess_run_id=reprocess_run_id,
                            session_id=target_session_id,
                            error=error,
                        )
                    )
        if failures:
            with session_factory.begin() as session:
                reprocess_run = session.get(IntelligenceReprocessRun, reprocess_run_id, with_for_update=True)
                assert reprocess_run is not None
                from datetime import UTC, datetime
                reprocess_run.result = {"completed_sessions": results, "failed_sessions": failures}
                reprocess_run.status = "PARTIAL_FAILED"
                reprocess_run.completed_at = datetime.now(UTC)
                reprocess_run.error = failures[0]["error"]
                reprocess_run.failed_at = datetime.now(UTC)
            raise RuntimeError("Intelligence reprocess has failed sessions; retry will resume only those sessions.")
        try:
            with session_factory.begin() as session:
                reprocess_run = session.get(IntelligenceReprocessRun, reprocess_run_id, with_for_update=True)
                assert reprocess_run is not None
                activation = activate_reprocess_scope(session, reprocess_run_id=reprocess_run_id)
                from datetime import UTC, datetime
                reprocess_run.result = {
                    "completed_sessions": results,
                    "failed_sessions": [],
                    "activation": activation,
                }
                reprocess_run.status = "COMPLETED"
                reprocess_run.completed_at = datetime.now(UTC)
                reprocess_run.error = None
                reprocess_run.failed_at = None
        except Exception as error:
            with session_factory.begin() as session:
                reprocess_run = session.get(IntelligenceReprocessRun, reprocess_run_id, with_for_update=True)
                assert reprocess_run is not None
                from datetime import UTC, datetime
                reprocess_run.status = "FAILED"
                reprocess_run.error = f"{type(error).__name__}: {error}"[:1000]
                reprocess_run.failed_at = datetime.now(UTC)
            raise
        return {
            "reprocess_run_id": raw_run_id,
            "completed_sessions": results,
            "failed_sessions": [],
            "activation": activation,
        }

    registry.register(INTELLIGENCE_REPROCESS_JOB, handle_reprocess)
