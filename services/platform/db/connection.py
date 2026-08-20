"""SQLAlchemy connection helpers for the managed PostgreSQL database."""

from functools import lru_cache

from sqlalchemy import Engine, create_engine

from services.platform.config import get_settings


def normalize_database_url(database_url: str) -> str:
    """Use the psycopg 3 SQLAlchemy driver for PostgreSQL URLs."""

    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgres://")
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    return database_url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine."""

    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required to use the database. "
            "Set it before creating a database engine."
        )

    return create_engine(
        normalize_database_url(database_url),
        pool_pre_ping=True,
    )


def reset_engine_cache() -> None:
    """Clear the cached engine for tests and controlled reloads."""

    get_engine.cache_clear()