#!/usr/bin/env python3
"""Resume the durable interaction/Tutor proof for one accepted Full-Power CREATE Scene."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from scripts.test_postgres import test_database_url
from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
from services.platform.config import reset_settings_cache
from services.platform.config.settings import Settings
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import AIExecution, LearningMessage, StudioCanvasSpecialistRun, StudioScene, StudioStudentInteraction, Student, User
from services.platform.db.session import get_session
from services.platform.db.test_environment import require_disposable_test_database
from services.platform.storage import create_object_storage
from scripts.prove_studio_agentic_live import semantic_action_for_scene


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--run-id", type=UUID, required=True)
    parser.add_argument("--scene-id", type=UUID, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package-output", type=Path)
    parser.add_argument("--package-only", action="store_true")
    args = parser.parse_args()

    database_url = test_database_url()
    require_disposable_test_database(database_url, environ={"LINA_TEST_DATABASE": "1"})
    settings = Settings(_env_file=args.env_file, database_url=database_url, model_provider="openai")
    if settings.model_api_key is None or settings.model_name == "mock":
        raise SystemExit("Configured MODEL_API_KEY and a real MODEL_NAME are required.")
    os.environ.update({
        "DATABASE_URL": database_url,
        "LINA_TEST_DATABASE": "1",
        "MODEL_PROVIDER": "openai",
        "MODEL_NAME": settings.model_name,
        "MODEL_API_KEY": settings.model_api_key.get_secret_value(),
        "STORAGE_PROVIDER": settings.storage_provider,
        "STORAGE_DIR": str(settings.storage_dir),
    })
    if settings.model_base_url:
        os.environ["MODEL_BASE_URL"] = settings.model_base_url
    reset_settings_cache()

    engine = create_engine(normalize_database_url(database_url))
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        run = session.get(StudioCanvasSpecialistRun, args.run_id)
        if run is None or run.scene_id != args.scene_id:
            raise RuntimeError("CREATE_RUN_OR_SCENE_NOT_FOUND")
        scene = session.get(StudioScene, args.scene_id)
        custom = next((block for block in (scene.seed_payload if scene else {}).get("blocks", []) if block.get("type") == "CUSTOM_VISUAL"), None)
        if not isinstance(custom, dict) or not isinstance(custom.get("custom_visual_build_id"), str):
            raise RuntimeError("CREATE_CUSTOM_BUILD_REFERENCE_MISSING")
        build_id = UUID(custom["custom_visual_build_id"])
        user = session.scalar(select(User).join(Student).where(Student.id == run.student_id))
        if user is None:
            raise RuntimeError("CREATE_RUN_OWNER_NOT_FOUND")
        student_id, runtime_id, learning_session_id, subject = run.student_id, run.studio_runtime_id, run.learning_session_id, user.external_subject
        storage = create_object_storage(settings)
        resolved = __import__("services.studio.custom_visual_builds", fromlist=["resolve_custom_visual_build"]).resolve_custom_visual_build(
            session, storage=storage, build_id=build_id, student_id=student_id, runtime_id=runtime_id,
        )
        if args.package_output is not None:
            args.package_output.parent.mkdir(parents=True, exist_ok=True)
            args.package_output.write_text(resolved.package.model_dump_json(indent=2), encoding="utf-8")
        if args.package_only:
            return

    def database_session():
        with factory.begin() as session:
            yield session

    from apps.api.main import app

    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject=subject, role=UserRole.STUDENT, email=f"{subject}@example.test"
    )
    try:
        client = TestClient(app, raise_server_exceptions=True)
        snapshot = client.get(f"/api/v1/student/studio/{runtime_id}/snapshot")
        if snapshot.status_code != 200:
            raise RuntimeError("CREATE_SCENE_SNAPSHOT_UNAVAILABLE")
        operation = client.post(
            f"/api/v1/student/studio/{runtime_id}/operations",
            json={
                "scene_id": str(args.scene_id),
                "base_scene_version": snapshot.json()["current_scene_version"],
                **semantic_action_for_scene(snapshot.json()["state_payload"]["agentic_canvas"]),
                "idempotency_key": f"full-power-create-resume:{uuid4()}",
            },
        )
        if operation.status_code != 200:
            raise RuntimeError(f"CREATE_SEMANTIC_ACTION_REJECTED:{operation.text}")
        interaction_id = UUID(operation.json()["student_interaction_id"])
        turn = client.post(f"/api/v1/student/studio/{runtime_id}/interactions/{interaction_id}/turn/stream")
        if turn.status_code != 200 or "event: turn" not in turn.text:
            raise RuntimeError("CREATE_SAME_TUTOR_STREAM_FAILED")
        with factory() as session:
            interaction = session.get(StudioStudentInteraction, interaction_id)
            message = session.get(LearningMessage, interaction.tutor_message_id) if interaction else None
            execution = session.get(AIExecution, interaction.ai_execution_id) if interaction else None
            if interaction is None or interaction.status != "COMPLETED" or message is None or execution is None:
                raise RuntimeError("CREATE_SAME_TUTOR_CONTINUITY_MISSING")
            output = {
                "status": "COMPLETED",
                "run_id": str(args.run_id),
                "scene_id": str(args.scene_id),
                "build_id": str(build_id),
                "student_id": str(student_id),
                "runtime_id": str(runtime_id),
                "interaction_id": str(interaction_id),
                "tutor_message_id": str(message.id),
                "tutor_execution_id": str(execution.id),
                "tutor_response": message.content,
            }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(output, separators=(",", ":")))
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_principal, None)
        engine.dispose()


if __name__ == "__main__":
    main()
