#!/usr/bin/env python3
"""Manage Lina's one disposable PostgreSQL test database and run its suite."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.engine import URL, make_url

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.platform.db.test_environment import (
    CANONICAL_TEST_DATABASE_NAME,
    require_disposable_test_database,
)


CONTAINER_NAME = "lina-learning-test-postgres"
VOLUME_NAME = "lina-learning-test-postgres-data"
POSTGRES_IMAGE = "pgvector/pgvector:0.8.1-pg17"
POSTGRES_USER = "lina_test"
POSTGRES_PASSWORD = "lina_test"
DEFAULT_PORT = 55434


def test_database_url() -> str:
    """Return the only allowed local/CI integration-test database URL."""

    configured = os.getenv("LINA_TEST_DATABASE_URL")
    if configured:
        return configured
    port = os.getenv("LINA_TEST_DATABASE_PORT", str(DEFAULT_PORT))
    return URL.create(
        "postgresql+psycopg",
        username=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host="127.0.0.1",
        port=int(port),
        database=CANONICAL_TEST_DATABASE_NAME,
    ).render_as_string(hide_password=False)


def test_environment(database_url: str) -> dict[str, str]:
    """Build an isolated runtime environment that overrides any local .env."""

    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": database_url,
            "LINA_TEST_DATABASE": "1",
            "MODEL_PROVIDER": "mock",
        }
    )
    require_disposable_test_database(database_url, environ=environment)
    return environment


def _run(command: Sequence[str], *, environment: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=ROOT, env=environment, check=True)


def _docker(*arguments: str) -> None:
    _run(("docker", *arguments))


def _container_exists() -> bool:
    result = subprocess.run(
        ("docker", "container", "inspect", CONTAINER_NAME),
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def down() -> None:
    """Remove only the named disposable container and its named data volume."""

    if _container_exists():
        _docker("rm", "--force", CONTAINER_NAME)
    _docker("volume", "rm", "--force", VOLUME_NAME)


def up(database_url: str) -> None:
    """Start a clean local pgvector PostgreSQL container and wait for health."""

    parsed = make_url(database_url)
    if parsed.host not in {"127.0.0.1", "localhost"}:
        raise RuntimeError(
            "The local test database runner only starts localhost. "
            "Set LINA_TEST_DATABASE_MANAGED_EXTERNALLY=1 for CI services."
        )
    port = parsed.port or DEFAULT_PORT
    down()
    _docker("volume", "create", VOLUME_NAME)
    _docker(
        "run",
        "--detach",
        "--name",
        CONTAINER_NAME,
        "--publish",
        f"127.0.0.1:{port}:5432",
        "--volume",
        f"{VOLUME_NAME}:/var/lib/postgresql/data",
        "--env",
        f"POSTGRES_DB={CANONICAL_TEST_DATABASE_NAME}",
        "--env",
        f"POSTGRES_USER={POSTGRES_USER}",
        "--env",
        f"POSTGRES_PASSWORD={POSTGRES_PASSWORD}",
        "--health-cmd",
        f"pg_isready -U {POSTGRES_USER} -d {CANONICAL_TEST_DATABASE_NAME}",
        "--health-interval",
        "1s",
        "--health-timeout",
        "5s",
        "--health-retries",
        "30",
        POSTGRES_IMAGE,
    )
    for _ in range(30):
        status = subprocess.run(
            ("docker", "inspect", "--format", "{{.State.Health.Status}}", CONTAINER_NAME),
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if status.returncode == 0 and status.stdout.strip() == "healthy":
            return
        time.sleep(1)
    raise RuntimeError("Disposable PostgreSQL did not become healthy within 30 seconds.")


def migrate(environment: dict[str, str]) -> None:
    """Apply the production Alembic history to the disposable test database."""

    _run((sys.executable, "-m", "alembic", "upgrade", "head"), environment=environment)


def run_pytest(environment: dict[str, str]) -> None:
    """Run every Python test with PostgreSQL suites enabled by the test boundary."""

    _run((sys.executable, "-m", "pytest", "-q"), environment=environment)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("up", "down", "reset", "migrate", "test"))
    args = parser.parse_args()

    database_url = test_database_url()
    environment = test_environment(database_url)
    externally_managed = os.getenv("LINA_TEST_DATABASE_MANAGED_EXTERNALLY") == "1"

    if args.action == "down":
        if externally_managed:
            return
        down()
        return
    if args.action == "up":
        if not externally_managed:
            up(database_url)
        return
    if args.action == "reset":
        if not externally_managed:
            up(database_url)
        migrate(environment)
        return
    if args.action == "migrate":
        migrate(environment)
        return

    try:
        if not externally_managed:
            up(database_url)
        migrate(environment)
        run_pytest(environment)
    finally:
        if not externally_managed:
            down()


if __name__ == "__main__":
    main()
