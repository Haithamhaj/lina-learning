#!/usr/bin/env python3
"""Create bounded real PostgreSQL lineage for Agentic Canvas LIVE-09--11."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from scripts.prove_studio_agentic_live import _durable_studio_evidence, semantic_action_for_scene
from scripts.test_postgres import test_database_url
from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
from services.platform.config import reset_settings_cache
from services.platform.config.settings import Settings
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    AIExecution,
    Job,
    JobStatus,
    LearningMessage,
    StudioCanvasSpecialistRun,
    StudioStudentInteraction,
)
from services.platform.db.session import get_session
from services.platform.db.test_environment import require_disposable_test_database
from services.platform.storage import create_object_storage
from workers.agentic_canvas_handlers import register_agentic_canvas_handlers
from workers.job_worker import JobHandlerRegistry, run_once


INITIAL_REQUEST = (
    "Open Canvas and create an interactive number line comparing 0.407 and 0.47. "
    "Use an exact calculation to verify the comparison, then let me select 0.47. "
    "After that Canvas selection, respond in Chat and update Canvas to emphasize "
    "why 0.47 is larger. Do not use a prepared activity."
)
SUCCESSOR_REQUEST = (
    "Replace the active Canvas with a fresh interactive comparison of 5/8 and 3/4, "
    "preserving exact fraction values and letting me select the larger value."
)


def _write(output: Path, evidence: dict[str, object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    temporary.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(output)


def _consume_tutor_turn(response) -> None:
    if response.status_code != 200 or "event: turn" not in response.text:
        raise RuntimeError("REAL_TUTOR_STREAM_DID_NOT_COMPLETE")


def _latest_run(factory: sessionmaker[Session], learning_session_id: UUID) -> StudioCanvasSpecialistRun:
    with factory() as session:
        run = session.scalar(
            select(StudioCanvasSpecialistRun)
            .where(StudioCanvasSpecialistRun.learning_session_id == learning_session_id)
            .order_by(StudioCanvasSpecialistRun.created_at.desc(), StudioCanvasSpecialistRun.id.desc())
        )
        if run is None:
            raise RuntimeError("TUTOR_CANVAS_BRIEF_DID_NOT_CREATE_RUN")
        session.expunge(run)
        return run


def _configure_runtime(settings: Settings, database_url: str) -> None:
    os.environ.update({
        "DATABASE_URL": database_url,
        "LINA_TEST_DATABASE": "1",
        "MODEL_PROVIDER": "openai",
        "MODEL_NAME": settings.model_name,
        "MODEL_API_KEY": settings.model_api_key.get_secret_value(),  # type: ignore[union-attr]
    })
    if settings.model_base_url:
        os.environ["MODEL_BASE_URL"] = settings.model_base_url
    reset_settings_cache()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("output/studio-agentic-durable-live-proof.json"))
    args = parser.parse_args()
    if not args.live:
        raise SystemExit("Refusing real provider calls without --live.")

    database_url = test_database_url()
    require_disposable_test_database(database_url, environ={"LINA_TEST_DATABASE": "1"})
    settings = Settings(
        _env_file=args.env_file,
        database_url=database_url,
        model_provider="openai",
        allowed_origins=["http://localhost:5000"],
    )
    if settings.model_api_key is None or settings.model_name == "mock":
        raise SystemExit("Configured MODEL_API_KEY and a real MODEL_NAME are required.")
    _configure_runtime(settings, database_url)

    engine = create_engine(normalize_database_url(database_url))
    factory = sessionmaker(engine, expire_on_commit=False)
    proof_subject = f"studio-agentic-live-{uuid4().hex}"
    evidence: dict[str, object] = {
        "proof": "STUDIO-AGENTIC-01-DURABLE",
        "schema_version": "studio-agentic-durable-live-proof-v1",
        "status": "RUNNING",
        "stage": "STARTED",
    }
    _write(args.output, evidence)

    def database_session():
        with factory.begin() as session:
            yield session

    from apps.api.main import app

    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject=proof_subject,
        role=UserRole.STUDENT,
        email=f"{proof_subject}@example.test",
    )
    client = TestClient(app, raise_server_exceptions=True)
    try:
        opened = client.post("/api/v1/student/daily/session")
        if opened.status_code != 200:
            raise RuntimeError("DAILY_SESSION_OPEN_FAILED")
        learning_session_id = UUID(opened.json()["learning_session_id"])
        runtime_response = client.post(f"/api/v1/student/studio/session/{learning_session_id}/open")
        if runtime_response.status_code != 200:
            raise RuntimeError("STUDIO_RUNTIME_OPEN_FAILED")
        runtime_id = UUID(runtime_response.json()["runtime_id"])
        evidence.update(stage="RUNTIME_OPEN", learning_session_id=str(learning_session_id), runtime_id=str(runtime_id))
        _write(args.output, evidence)

        _consume_tutor_turn(client.post(
            f"/api/v1/student/daily/session/{learning_session_id}/turn/stream",
            json={"content": INITIAL_REQUEST},
        ))
        initial_run = _latest_run(factory, learning_session_id)
        if initial_run.job_id is None:
            raise RuntimeError("INITIAL_AGENT_JOB_MISSING")
        evidence.update(stage="INITIAL_BRIEF_ADMITTED", run_id=str(initial_run.id))
        _write(args.output, evidence)

        registry = JobHandlerRegistry()
        register_agentic_canvas_handlers(
            registry,
            session_factory=factory,
            settings_factory=lambda: settings,
            storage=create_object_storage(settings),
        )
        worker_status = run_once(
            factory,
            registry,
            worker_id=f"studio-agentic-live-{uuid4().hex[:8]}",
            job_ids={initial_run.job_id},
        )
        if worker_status is JobStatus.PENDING:
            with factory() as session:
                retry_job = session.get(Job, initial_run.job_id)
                if retry_job is None:
                    raise RuntimeError("INITIAL_AGENT_RETRY_JOB_MISSING")
                retry_at = retry_job.run_after
            worker_status = run_once(
                factory,
                registry,
                worker_id=f"studio-agentic-live-retry-{uuid4().hex[:8]}",
                now=retry_at,
                job_ids={initial_run.job_id},
            )
        if worker_status is not JobStatus.COMPLETED:
            raise RuntimeError(f"INITIAL_AGENT_JOB_{worker_status}")
        with factory() as session:
            settled = session.get(StudioCanvasSpecialistRun, initial_run.id)
            if settled is None or settled.scene_id is None or settled.status != "COMPLETED":
                raise RuntimeError("INITIAL_AGENT_SCENE_NOT_SETTLED")
            scene_id = settled.scene_id

        snapshot = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot")
        if snapshot.status_code != 200 or snapshot.json().get("active_scene_seed") is None:
            raise RuntimeError("ACTIVE_AGENT_SCENE_NOT_AVAILABLE")
        snapshot_payload = snapshot.json()
        semantic_action = semantic_action_for_scene(
            snapshot_payload["active_scene_seed"], preferred_value="0.47"
        )
        operation = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(scene_id),
                "base_scene_version": snapshot_payload["current_scene_version"],
                "action_key": semantic_action["action_key"],
                "payload": semantic_action["payload"],
                "idempotency_key": f"studio-agentic-live-action:{uuid4()}",
            },
        )
        if operation.status_code != 200 or operation.json().get("student_interaction_id") is None:
            raise RuntimeError("SEMANTIC_CANVAS_ACTION_NOT_ADMITTED")
        interaction_id = UUID(operation.json()["student_interaction_id"])
        _consume_tutor_turn(client.post(
            f"/api/v1/student/studio/{runtime_id}/interactions/{interaction_id}/turn/stream"
        ))
        with factory() as session:
            interaction = session.get(StudioStudentInteraction, interaction_id)
            message = session.get(LearningMessage, interaction.tutor_message_id) if interaction is not None else None
            execution = session.get(AIExecution, interaction.ai_execution_id) if interaction is not None else None
            update_run = session.scalar(
                select(StudioCanvasSpecialistRun).where(
                    StudioCanvasSpecialistRun.source_message_id == message.id,
                    StudioCanvasSpecialistRun.base_scene_id == scene_id,
                )
            ) if message is not None else None
            if (
                interaction is None or interaction.status != "COMPLETED"
                or message is None or execution is None
                or message.ai_execution_id != interaction.ai_execution_id
                or update_run is None
            ):
                raise RuntimeError("CAUSAL_SAME_TUTOR_CANVAS_UPDATE_MISSING")
            update_run_id = update_run.id
        evidence.update(
            stage="CAUSAL_UPDATE_ADMITTED",
            scene_id=str(scene_id),
            interaction_id=str(interaction_id),
            update_run_id=str(update_run_id),
        )
        _write(args.output, evidence)

        _consume_tutor_turn(client.post(
            f"/api/v1/student/daily/session/{learning_session_id}/turn/stream",
            json={"content": SUCCESSOR_REQUEST},
        ))
        successor = _latest_run(factory, learning_session_id)
        if successor.id == update_run_id:
            raise RuntimeError("NEWER_TUTOR_CANVAS_SUCCESSOR_MISSING")

        durable = _durable_studio_evidence(settings, initial_run.id)
        if (
            durable["interaction_status"] != "COMPLETED"
            or durable["scene_status"] != "ACTIVE"
            or durable["update_run_id"] != str(update_run_id)
            or durable["successor_run_id"] != str(successor.id)
            or durable["superseded_run_id"] != str(update_run_id)
        ):
            raise RuntimeError("DURABLE_LIVE_LINEAGE_INSPECTION_FAILED")
        evidence.update(status="COMPLETED", stage="VERIFIED", successor_run_id=str(successor.id), durable=durable)
        _write(args.output, evidence)
        print(json.dumps({
            "proof": evidence["proof"],
            "status": evidence["status"],
            "run_id": str(initial_run.id),
            "evidence_path": str(args.output),
        }, separators=(",", ":")))
    except BaseException as error:
        evidence.update(status="FAILED", exception_type=type(error).__name__)
        _write(args.output, evidence)
        raise
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_principal, None)
        engine.dispose()


if __name__ == "__main__":
    main()
