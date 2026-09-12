"""Loopback-only disposable-owner harness for the production Studio browser path.

Authentication is supplied for a verified disposable proof owner. All snapshot,
Build, operation and Primary Tutor routes are the actual application endpoints.
No production login or real-learner acceptance is claimed by this harness.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from uuid import UUID

import uvicorn
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from scripts.prove_studio_agentic_durable_live import _configure_runtime
from scripts.test_postgres import test_database_url
from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
from services.platform.config.settings import Settings
from services.platform.db.models import StudioCanvasSpecialistRun, Student, User
from services.platform.db.session import get_session
from services.platform.db.test_environment import require_disposable_test_database


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--run-id", type=UUID, required=True)
    parser.add_argument("--port", type=int, default=5179)
    parser.add_argument("--harness", type=Path, default=Path("/tmp/lina-full-power-live"))
    args = parser.parse_args()
    database_url = test_database_url()
    require_disposable_test_database(database_url, environ={"LINA_TEST_DATABASE": "1"})
    settings = Settings(_env_file=args.env_file, database_url=database_url, model_provider="openai")
    _configure_runtime(settings, database_url)
    factory = sessionmaker(create_engine(database_url), expire_on_commit=False)
    with factory() as session:
        run = session.get(StudioCanvasSpecialistRun, args.run_id)
        if run is None or run.scene_id is None:
            raise RuntimeError("Accepted proof run is required")
        user = session.scalar(select(User).join(Student).where(Student.id == run.student_id))
        if user is None or not user.external_subject.startswith("studio-agentic-live-"):
            raise RuntimeError("Only an existing disposable live-proof owner is allowed")
        subject, runtime = user.external_subject, run.studio_runtime_id

    def database_session():
        with factory.begin() as session:
            yield session

    from apps.api.main import app
    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject=subject, role=UserRole.STUDENT, email=f"{subject}@example.test")
    app.mount("/", StaticFiles(directory=args.harness, html=True), name="disposable-browser-proof")
    print(f"http://127.0.0.1:{args.port}/?runtime={runtime}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
