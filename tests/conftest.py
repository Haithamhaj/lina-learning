"""Global test safety boundaries."""

from __future__ import annotations

import os

from services.platform.db.test_environment import require_disposable_test_database


def pytest_sessionstart() -> None:
    """Refuse destructive PostgreSQL fixtures outside the disposable test DB."""

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        require_disposable_test_database(database_url, environ=os.environ)
