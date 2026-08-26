from pathlib import Path

import pytest
from pydantic import ValidationError

from services.platform.config import Settings


def test_development_configuration_has_safe_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.storage_provider == "local"
    assert settings.model_provider == "mock"
    assert settings.allowed_origins == ["http://localhost:5000"]
    assert settings.session_secret is None
    assert settings.s3_multipart_threshold_bytes == 8 * 1024 * 1024
    assert settings.tutor_max_output_tokens == 2000


def test_tutor_output_ceiling_reads_a_positive_environment_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TUTOR_MAX_OUTPUT_TOKENS", "2400")

    settings = Settings(_env_file=None)

    assert settings.tutor_max_output_tokens == 2400


@pytest.mark.parametrize("value", [0, -1])
def test_tutor_output_ceiling_rejects_non_positive_values(value: int) -> None:
    with pytest.raises(ValidationError, match="tutor_max_output_tokens"):
        Settings(_env_file=None, tutor_max_output_tokens=value)


def test_allowed_origins_accepts_explicit_list() -> None:
    settings = Settings(
        _env_file=None,
        allowed_origins=["https://app.example.com", "https://admin.example.com"],
    )

    assert settings.allowed_origins == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


@pytest.mark.parametrize(
    "field,value",
    [
        ("web_origin", ""),
        ("web_origin", "https://app.example.com/path"),
        ("web_origin", "https://example .com"),
        ("web_origin", "https://example.com%2f.evil.test"),
        ("allowed_origins", ["https://app.example.com/path"]),
    ],
)
def test_trusted_origin_configuration_rejects_missing_or_non_origin_values(
    field: str,
    value: str | list[str],
) -> None:
    with pytest.raises(ValidationError, match="origin"):
        Settings(_env_file=None, **{field: value})


def test_production_configuration_fails_with_clear_missing_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("APP_ENV", "SESSION_SECRET", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError, match="SESSION_SECRET"):
        Settings(_env_file=None, app_env="production")


def test_production_configuration_rejects_local_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("APP_ENV", "SESSION_SECRET", "DATABASE_URL", "STORAGE_PROVIDER"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError, match="STORAGE_PROVIDER"):
        Settings(
            _env_file=None,
            app_env="production",
            session_secret="s",
            database_url="postgresql://localhost/db",
            storage_provider="local",
        )


def test_s3_configuration_requires_private_storage_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "STORAGE_PROVIDER",
        "S3_BUCKET",
        "S3_REGION",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError, match="S3_BUCKET"):
        Settings(_env_file=None, storage_provider="s3")


def test_model_provider_requires_api_key_when_not_mock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("MODEL_PROVIDER", "MODEL_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError, match="MODEL_API_KEY"):
        Settings(_env_file=None, model_provider="openai")


def test_secret_values_are_masked_by_pydantic() -> None:
    settings = Settings(_env_file=None, session_secret="do-not-log-this")

    assert str(settings.session_secret) == "**********"
    assert "do-not-log-this" not in repr(settings)


def test_frontend_source_only_uses_browser_safe_configuration() -> None:
    web_sources = "\n".join(
        path.read_text()
        for path in Path("apps/web").rglob("*")
        if path.suffix in {".ts", ".tsx", ".js", ".mjs"}
            and ".next" not in path.parts
            and "node_modules" not in path.parts
    )

    for server_secret_name in (
        "SESSION_SECRET",
        "DATABASE_URL",
        "S3_SECRET_ACCESS_KEY",
        "MODEL_API_KEY",
        "CLERK_SECRET_KEY",
    ):
        assert server_secret_name not in web_sources

    assert "NEXT_PUBLIC_API_BASE_URL" in web_sources
