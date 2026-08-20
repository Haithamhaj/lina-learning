"""Typed environment configuration for the Lina foundation.

Only this server-side module reads secrets. The web application has a separate
public configuration module that reads NEXT_PUBLIC_* values only.
"""

from functools import lru_cache
from ipaddress import ip_address
from pathlib import Path
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["development", "test", "production"]
StorageProvider = Literal["local", "s3"]
ModelProvider = Literal["mock", "openai"]
_HOSTNAME_PATTERN = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z"
)


def _normalize_hostname(hostname: str) -> str:
    """Validate and normalize a DNS or IP hostname for an allowed origin."""

    try:
        return str(ip_address(hostname))
    except ValueError:
        try:
            normalized = hostname.encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise ValueError("Trusted origin has an invalid hostname.") from exc

    if not _HOSTNAME_PATTERN.fullmatch(normalized):
        raise ValueError("Trusted origin has an invalid hostname.")
    return normalized


def _normalize_trusted_origin(value: str) -> str:
    """Return a browser-origin form suitable for CORS and Clerk ``azp`` checks."""

    origin = value.strip() if isinstance(value, str) else ""
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Trusted origin must be an absolute http(s) origin.")

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Trusted origin has an invalid port.") from exc

    host = _normalize_hostname(parsed.hostname)
    if ":" in host:
        host = f"[{host}]"
    if port is not None and (parsed.scheme, port) not in {("http", 80), ("https", 443)}:
        host = f"{host}:{port}"
    return f"{parsed.scheme.lower()}://{host}"


class Settings(BaseSettings):
    """Validated server configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: EnvironmentName = "development"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    web_origin: str = "http://localhost:5000"
    allowed_origins: list[str] = Field(default_factory=list)

    # Clerk publishable configuration is safe to use for JWT key discovery.
    # The secret key remains managed by Clerk and is never read by the browser.
    clerk_publishable_key: str | None = None
    clerk_jwks_url: str | None = None

    # Server-only secret. SecretStr prevents accidental plaintext repr/logging.
    session_secret: SecretStr | None = None

    # Database settings are defined now; the database implementation belongs to
    # TASK-003 and must not be initialized as part of this task.
    database_url: str | None = None

    # Provider-neutral object storage settings. Production can use any service
    # that implements the S3 API, including an optional custom endpoint.
    storage_provider: StorageProvider = "local"
    storage_dir: Path = Path(".local/storage")
    s3_endpoint: str | None = None
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_multipart_threshold_bytes: int = Field(
        default=8 * 1024 * 1024,
        gt=0,
    )

    # Model routing settings. Provider calls remain deferred to the Model
    # Gateway task; mock is the safe foundation default.
    model_provider: ModelProvider = "mock"
    model_name: str = "mock"
    model_base_url: str | None = None
    model_api_key: SecretStr | None = None

    @model_validator(mode="after")
    def validate_service_requirements(self) -> "Settings":
        """Fail clearly when an enabled deployment mode is incomplete."""

        self.web_origin = _normalize_trusted_origin(self.web_origin)
        if not self.allowed_origins:
            self.allowed_origins = [self.web_origin]
        self.allowed_origins = list(
            dict.fromkeys(_normalize_trusted_origin(origin) for origin in self.allowed_origins)
        )

        missing: list[str] = []
        if self.app_env == "production":
            if self.session_secret is None:
                missing.append("SESSION_SECRET")
            if not self.database_url:
                missing.append("DATABASE_URL")
            if self.storage_provider == "local":
                missing.append("STORAGE_PROVIDER (must not be 'local' in production)")

        if self.storage_provider == "s3":
            for name, value in (
                ("S3_BUCKET", self.s3_bucket),
                ("S3_REGION", self.s3_region),
                ("S3_ACCESS_KEY_ID", self.s3_access_key_id),
                ("S3_SECRET_ACCESS_KEY", self.s3_secret_access_key),
            ):
                if value is None:
                    missing.append(name)

        if self.model_provider != "mock" and self.model_api_key is None:
            missing.append("MODEL_API_KEY")

        if missing:
            joined = ", ".join(missing)
            raise ValueError(
                f"Configuration is incomplete for APP_ENV={self.app_env}: "
                f"missing {joined}. Set these values before starting."
            )

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""

    return Settings()


def reset_settings_cache() -> None:
    """Clear the cached settings instance for tests and controlled reloads."""

    get_settings.cache_clear()
