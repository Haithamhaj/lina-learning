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
from services.platform.db.models import AIExecution, LearningMessage, StudioCanvasSpecialistRun, StudioStudentInteraction, Student, User
from services.platform.db.session import get_session
from services.platform.db.test_environment import require_disposable_test_database
from services.platform.storage import create_object_storage
from services.studio.custom_visual_builds import CustomVisualBuildResolver, repair_custom_visual_source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--run-id", type=UUID, required=True)
    parser.add_argument("--scene-id", type=UUID, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package-output", type=Path)
    parser.add_argument("--package-only", action="store_true")
    parser.add_argument("--repair-source-only", action="store_true")
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
        user = session.scalar(select(User).join(Student).where(Student.id == run.student_id))
        if user is None:
            raise RuntimeError("CREATE_RUN_OWNER_NOT_FOUND")
        student_id, runtime_id, learning_session_id, subject = run.student_id, run.studio_runtime_id, run.learning_session_id, user.external_subject
        storage = create_object_storage(settings)
        resolved = __import__("services.studio.custom_visual_builds", fromlist=["resolve_custom_visual_build"]).resolve_custom_visual_build(
            session, storage=storage, build_id=UUID("555f790a-c452-49df-b009-b0178a403783"), student_id=student_id, runtime_id=runtime_id, allow_source_layout_repair=args.repair_source_only,
        )
        if args.repair_source_only:
            source = resolved.package.source
            old_append = "panel.parentNode.appendChild(b);"
            old_position = "btnA.style.position='absolute'; btnA.style.left='650px'; btnA.style.top='295px';\n  btnB.style.position='absolute'; btnB.style.left='765px'; btnB.style.top='295px';"
            if old_append not in source or old_position not in source:
                raise RuntimeError("SOURCE_ONLY_REPAIR_PATTERN_NOT_FOUND")
            repaired = source.replace(old_append, "root.appendChild(b);").replace(
                old_position,
                "root.style.display='grid'; root.style.gap='8px'; root.style.justifyItems='start';",
            )
            build = repair_custom_visual_source(
                session,
                storage=storage,
                run=run,
                parent=resolved,
                repaired_source=repaired,
            )
            session.commit()
            resolved = CustomVisualBuildResolver(storage).resolve(
                session, build_id=build.id, student_id=student_id, runtime_id=runtime_id,
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
                "action_key": "SELECT",
                "payload": {
                    "version": "agentic-canvas-action-v1",
                    "action": "SELECT",
                    "block_id": "slope_compare_activity",
                    "element_id": "choice_b",
                    "from_value": None,
                    "to_value": None,
                },
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
                "build_id": "555f790a-c452-49df-b009-b0178a403783",
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
