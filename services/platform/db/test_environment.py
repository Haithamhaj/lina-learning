"""Fail-closed checks for Lina's disposable PostgreSQL test database."""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.engine import make_url


CANONICAL_TEST_DATABASE_NAME = "lina_learning_test"


class DisposableTestDatabaseError(RuntimeError):
    """Raised before a test can mutate a database outside the test boundary."""


def require_disposable_test_database(
    database_url: str,
    *,
    environ: Mapping[str, str],
) -> None:
    """Reject anything except the explicitly marked canonical test database."""

    if environ.get("LINA_TEST_DATABASE") != "1":
        raise DisposableTestDatabaseError(
            "PostgreSQL tests require LINA_TEST_DATABASE=1. "
            "Use the canonical test runner rather than a development database."
        )

    try:
        url = make_url(database_url)
    except Exception as exc:
        raise DisposableTestDatabaseError("DATABASE_URL is not a valid database URL.") from exc

    if url.get_backend_name() != "postgresql":
        raise DisposableTestDatabaseError("PostgreSQL tests require a PostgreSQL DATABASE_URL.")
    if url.database != CANONICAL_TEST_DATABASE_NAME:
        raise DisposableTestDatabaseError(
            "PostgreSQL tests require the canonical database "
            f"{CANONICAL_TEST_DATABASE_NAME!r}, not {url.database!r}."
        )
