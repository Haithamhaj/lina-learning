#!/usr/bin/env python3
"""Run one bounded real-provider Agentic Canvas Image Generation journey."""

from __future__ import annotations

import argparse
import json
import os
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from scripts.prove_studio_agentic_durable_live import (
    _configure_runtime,
    _consume_tutor_turn,
    _latest_run,
    _write,
)
from scripts.test_postgres import test_database_url
from services.platform.auth import (
    AuthenticatedPrincipal,
    UserRole,
    get_current_principal,
)
from services.platform.config.settings import Settings
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    Job,
    JobStatus,
    LearningMessage,
    StudioCanvasSpecialistRun,
    StudioGeneratedAsset,
    StudioScene,
    StudioSnapshot,
)
from services.platform.db.session import get_session
from services.platform.db.test_environment import require_disposable_test_database
from services.platform.storage import create_object_storage
from workers.agentic_canvas_handlers import register_agentic_canvas_handlers
from workers.job_worker import JobHandlerRegistry, run_once

IMAGE_REQUEST = (
    "Open Canvas and create one original illustrative image of a frog beside a pond, "
    "including irregular organic textures that typed geometric primitives cannot represent. "
    "Use Image Generation for the original illustration, keep labels and text out of the image, "
    "and add a simple typed diagram explaining the frog life cycle. This must be generated for "
    "this request, not selected from a prepared activity."
)


def _bounded_image_evidence(
    factory: sessionmaker[Session],
    *,
    run_id: UUID,
    storage,
) -> dict[str, object]:
    with factory() as session:
        run = session.get(StudioCanvasSpecialistRun, run_id)
        if run is None or run.job_id is None or run.scene_id is None:
            raise RuntimeError("IMAGE_AGENT_RUN_NOT_SETTLED")
        job = session.get(Job, run.job_id)
        scene = session.get(StudioScene, run.scene_id)
        snapshot = session.scalar(
            select(StudioSnapshot).where(StudioSnapshot.studio_runtime_id == run.studio_runtime_id)
        )
        source_message = session.get(LearningMessage, run.source_message_id)
        assets = list(session.scalars(
            select(StudioGeneratedAsset).where(StudioGeneratedAsset.source_run_id == run.id)
        ))
        if (
            job is None
            or job.status != JobStatus.COMPLETED
            or run.status != "COMPLETED"
            or scene is None
            or scene.status != "ACTIVE"
            or snapshot is None
            or snapshot.current_scene_id != scene.id
            or len(assets) != 1
            or source_message is None
            or source_message.ai_execution_id is None
        ):
            raise RuntimeError("IMAGE_DURABLE_LINEAGE_INCOMPLETE")
        image_blocks = [
            block for block in scene.seed_payload.get("blocks", [])
            if isinstance(block, dict) and block.get("type") == "IMAGE"
        ]
        asset = assets[0]
        if (
            len(image_blocks) != 1
            or image_blocks[0].get("studio_generated_asset_id") != str(asset.id)
            or "temporary_image_handle" in image_blocks[0]
            or "provider_url" in image_blocks[0]
        ):
            raise RuntimeError("IMAGE_BLOCK_ASSET_REFERENCE_INVALID")
        trace = run.agent_execution_metadata if isinstance(run.agent_execution_metadata, dict) else {}
        tool_calls = trace.get("tool_calls") if isinstance(trace.get("tool_calls"), list) else []
        image_calls = [
            call for call in tool_calls
            if isinstance(call, dict)
            and call.get("name") == "image_generation"
            and call.get("status") == "completed"
        ]
        if len(image_calls) != 1:
            raise RuntimeError("DURABLE_IMAGE_TOOL_TRACE_MISSING")
        stored = storage.head(asset.storage_key)
        if (
            stored.checksum_sha256 != asset.checksum_sha256
            or stored.size != asset.size_bytes
            or stored.content_type != asset.content_type
        ):
            raise RuntimeError("OBJECT_STORAGE_IMAGE_MISMATCH")
        return {
            "tutor_execution_id": str(source_message.ai_execution_id),
            "canvas_brief_digest": run.order_digest,
            "run_id": str(run.id),
            "sdk_trace_id": run.sdk_trace_id,
            "selected_tools": trace.get("selected_tools", []),
            "tool_call_count": trace.get("tool_call_count", 0),
            "image_tool_call_id": image_calls[0].get("call_id"),
            "image_tool_status": image_calls[0].get("status"),
            "proposal_digest": run.proposal_digest,
            "scene_id": str(scene.id),
            "scene_status": scene.status,
            "scene_contract": scene.payload_schema_version,
            "image_block_id": image_blocks[0].get("block_id"),
            "asset_id": str(asset.id),
            "asset_content_type": asset.content_type,
            "asset_size_bytes": asset.size_bytes,
            "asset_checksum_sha256": asset.checksum_sha256,
            "storage_key_digest": sha256(asset.storage_key.encode()).hexdigest(),
            "object_storage_verified": True,
            "active_snapshot_verified": True,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/studio-agentic-image-live-proof.json"),
    )
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
        storage_provider="local",
        storage_dir=args.output.parent / "studio-agentic-image-objects",
    )
    if settings.model_api_key is None or settings.model_name == "mock":
        raise SystemExit("Configured MODEL_API_KEY and a real MODEL_NAME are required.")
    _configure_runtime(settings, database_url)
    # The custom Responses client uses MODEL_API_KEY; the SDK trace exporter
    # receives the same already-authorized key without exposing or persisting it.
    os.environ["OPENAI_API_KEY"] = settings.model_api_key.get_secret_value()

    engine = create_engine(normalize_database_url(database_url))
    factory = sessionmaker(engine, expire_on_commit=False)
    storage = create_object_storage(settings)
    proof_subject = f"studio-agentic-image-{uuid4().hex}"
    evidence: dict[str, object] = {
        "proof": "STUDIO-AGENTIC-01-IMAGE",
        "schema_version": "studio-agentic-image-live-proof-v1",
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
    try:
        client = TestClient(app, raise_server_exceptions=True)
        opened = client.post("/api/v1/student/daily/session")
        if opened.status_code != 200:
            raise RuntimeError("DAILY_SESSION_OPEN_FAILED")
        learning_session_id = UUID(opened.json()["learning_session_id"])
        runtime_response = client.post(
            f"/api/v1/student/studio/session/{learning_session_id}/open"
        )
        if runtime_response.status_code != 200:
            raise RuntimeError("STUDIO_RUNTIME_OPEN_FAILED")

        _consume_tutor_turn(client.post(
            f"/api/v1/student/daily/session/{learning_session_id}/turn/stream",
            json={"content": IMAGE_REQUEST},
        ))
        run = _latest_run(factory, learning_session_id)
        if run.job_id is None:
            raise RuntimeError("IMAGE_AGENT_JOB_MISSING")
        evidence.update(stage="CANVAS_BRIEF_ADMITTED", run_id=str(run.id))
        _write(args.output, evidence)

        registry = JobHandlerRegistry()
        register_agentic_canvas_handlers(
            registry,
            session_factory=factory,
            settings_factory=lambda: settings,
            storage=storage,
        )
        worker_status = run_once(
            factory,
            registry,
            worker_id=f"studio-agentic-image-{uuid4().hex[:8]}",
            job_ids={run.job_id},
        )
        if worker_status is not JobStatus.COMPLETED:
            raise RuntimeError(f"IMAGE_AGENT_JOB_{worker_status}")

        bounded = _bounded_image_evidence(factory, run_id=run.id, storage=storage)
        evidence.update(status="COMPLETED", stage="VERIFIED", result=bounded)
        _write(args.output, evidence)
        print(json.dumps({
            "proof": evidence["proof"],
            "status": evidence["status"],
            "run_id": bounded["run_id"],
            "scene_id": bounded["scene_id"],
            "asset_id": bounded["asset_id"],
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
