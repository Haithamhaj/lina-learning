"""Safety contracts for the canonical disposable PostgreSQL test database."""

import pytest

from services.platform.db.test_environment import (
    DisposableTestDatabaseError,
    require_disposable_test_database,
)
from scripts.test_postgres import test_database_url as canonical_test_database_url


TEST_URL = "postgresql+psycopg://lina_test:lina_test@127.0.0.1:55434/lina_learning_test"


def test_disposable_database_requires_explicit_test_environment_flag() -> None:
    with pytest.raises(DisposableTestDatabaseError, match="LINA_TEST_DATABASE=1"):
        require_disposable_test_database(TEST_URL, environ={})


def test_disposable_database_rejects_a_development_database_name() -> None:
    with pytest.raises(DisposableTestDatabaseError, match="lina_learning_test"):
        require_disposable_test_database(
            "postgresql+psycopg://lina_test:lina_test@127.0.0.1:55434/lina_learning_demo",
            environ={"LINA_TEST_DATABASE": "1"},
        )


def test_disposable_database_accepts_only_the_canonical_test_database() -> None:
    require_disposable_test_database(TEST_URL, environ={"LINA_TEST_DATABASE": "1"})


def test_runner_default_url_keeps_its_test_only_password_for_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LINA_TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("LINA_TEST_DATABASE_PORT", raising=False)

    assert canonical_test_database_url() == TEST_URL
