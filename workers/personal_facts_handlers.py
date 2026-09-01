"""Worker-owned Personal Facts extraction job handler."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from services.model_gateway.factory import create_personal_facts_gateway
from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.personal_facts.extraction import (
    PERSONAL_FACTS_PROMPT_VERSION,
    PERSONAL_FACTS_SCHEMA_VERSION,
    PersonalFactsExtractionEnvelope,
    extraction_request,
    validate_extraction_output,
)
from services.personal_facts.reconciliation import reconcile_candidates
from services.platform.config import Settings, get_settings
from services.platform.db.models import Job, LearningMessage, LearningSession, ModelTask, PersonalFactExtractionRun

if TYPE_CHECKING:
    from workers.job_worker import JobHandlerRegistry


PERSONAL_FACTS_EXTRACTION_JOB = "PERSONAL_FACTS_EXTRACTION"


def register_personal_facts_handlers(
    registry: JobHandlerRegistry,
    *,
    session_factory: sessionmaker[Session],
    gateway_factory: Callable[[Session], ModelGateway] = create_personal_facts_gateway,
    settings: Settings | None = None,
) -> None:
    """Register the one PF-02 job in the existing durable Worker."""

    configured = settings or get_settings()

    def handle_personal_facts(job: Job) -> dict[str, object]:
        payload = job.payload if isinstance(job.payload, dict) else {}
        try:
            student_id = UUID(str(payload["student_id"]))
            session_id = UUID(str(payload["session_id"]))
        except (KeyError, ValueError, TypeError) as error:
            raise ValueError("PERSONAL_FACTS_EXTRACTION requires valid Student and Session lineage.") from error

        with session_factory() as session:
            learning_session = session.get(LearningSession, session_id, with_for_update=True)
            if (
                learning_session is None
                or learning_session.student_id != student_id
                or learning_session.status != "CLOSED"
            ):
                raise ValueError("PERSONAL_FACTS_EXTRACTION requires a closed matching Session.")
            run = session.execute(
                select(PersonalFactExtractionRun)
                .where(
                    PersonalFactExtractionRun.student_id == student_id,
                    PersonalFactExtractionRun.session_id == session_id,
                )
                .with_for_update()
            ).scalar_one_or_none()
            if run is not None and run.status in {"COMPLETED", "SKIPPED_CAPACITY"}:
                session.commit()
                return {"session_id": str(session_id), "outcome": run.status, "reused": True}
            if run is None:
                run = PersonalFactExtractionRun(
                    student_id=student_id,
                    session_id=session_id,
                    job_id=job.id,
                    status="PENDING",
                    schema_version=PERSONAL_FACTS_SCHEMA_VERSION,
                    prompt_version=PERSONAL_FACTS_PROMPT_VERSION,
                )
                session.add(run)
                session.flush()
            messages = list(session.scalars(
                select(LearningMessage)
                .where(LearningMessage.session_id == session_id)
                .order_by(LearningMessage.created_at, LearningMessage.id)
            ))
            if not any(message.role == "student" for message in messages):
                run.status = "COMPLETED"
                run.completed_at = datetime.now(UTC)
                run.failure_metadata = {"outcome": "NO_STUDENT_MESSAGES"}
                session.commit()
                return {"session_id": str(session_id), "outcome": "NO_STUDENT_MESSAGES", "candidate_count": 0}

            request = extraction_request(messages, learning_session=learning_session)
            # Capacity is the fully serialized Student source payload, not a
            # token estimate and never an invitation to truncate or chunk it.
            if len(str(request["input"])) > configured.personal_facts_context_capacity:
                run.status = "SKIPPED_CAPACITY"
                run.completed_at = datetime.now(UTC)
                run.failure_metadata = {"outcome": "SKIPPED_CAPACITY"}
                session.commit()
                return {"session_id": str(session_id), "outcome": "SKIPPED_CAPACITY", "candidate_count": 0}

            run.status = "RUNNING"
            run.started_at = run.started_at or datetime.now(UTC)
            session.flush()
            model_result = None
            try:
                model_result = gateway_factory(session).execute(
                    ModelTask.PERSONAL_FACTS,
                    request,
                    lineage=AIExecutionLineage(
                        operation="personal_facts_extraction",
                        operation_id=uuid5(NAMESPACE_URL, f"personal-facts-extraction:{session_id}"),
                        student_id=student_id,
                        learning_session_id=session_id,
                    ),
                )
                envelope = PersonalFactsExtractionEnvelope.model_validate(model_result.output)
                accepted = validate_extraction_output(
                    session,
                    student_id=student_id,
                    learning_session=learning_session,
                    envelope=envelope,
                )
                reconciliation = reconcile_candidates(
                    session,
                    student_id=student_id,
                    learning_session=learning_session,
                    candidates=accepted,
                )
            except ValidationError:
                # A malformed model response is a successful, safely empty
                # extraction—not an opportunity to persist unvalidated data.
                reconciliation = {"added": 0, "supported": 0, "noop": 0}
                accepted = []
            except Exception as error:
                run.status = "PENDING"
                run.failure_metadata = {"failure_type": type(error).__name__}
                session.commit()
                raise

            run.status = "COMPLETED"
            run.ai_execution_id = model_result.execution_id if model_result is not None else None
            run.completed_at = datetime.now(UTC)
            run.failure_metadata = {"candidate_count": len(accepted), "accepted_count": len(accepted)}
            session.commit()
            return {
                "session_id": str(session_id),
                "outcome": "COMPLETED",
                "candidate_count": len(accepted),
                **reconciliation,
            }

    registry.register(PERSONAL_FACTS_EXTRACTION_JOB, handle_personal_facts)
