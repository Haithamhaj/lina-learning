import os

import pytest

from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    Base,
    GradePeriod,
    Job,
    ParentStudentRelationship,
    Student,
    User,
)


def test_postgres_urls_use_psycopg_driver() -> None:
    assert (
        normalize_database_url("postgresql://db.example/lina")
        == "postgresql+psycopg://db.example/lina"
    )
    assert (
        normalize_database_url("postgres://db.example/lina")
        == "postgresql+psycopg://db.example/lina"
    )
    assert normalize_database_url("sqlite:///local.db") == "sqlite:///local.db"


def test_foundation_models_match_expected_tables() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "students",
        "parent_student_relationships",
        "grade_periods",
        "jobs",
        "ai_executions",
        "student_topic_boundaries",
        "safety_audits",
        "content_documents",
        "content_processing_runs",
        "curriculum_nodes",
        "content_blocks",
    }
    assert User.__tablename__ == "users"
    assert Student.__tablename__ == "students"
    assert ParentStudentRelationship.__tablename__ == "parent_student_relationships"
    assert GradePeriod.__tablename__ == "grade_periods"
    assert Job.__tablename__ == "jobs"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="development PostgreSQL is not available in this environment",
)
def test_development_schema_has_foundation_tables() -> None:
    """Inspect the real development schema after `alembic upgrade head`."""

    from sqlalchemy import inspect, text

    from services.platform.db.connection import get_engine

    inspector = inspect(get_engine())
    assert {
        "alembic_version",
        "users",
        "students",
        "parent_student_relationships",
        "grade_periods",
        "jobs",
        "ai_executions",
        "student_topic_boundaries",
        "safety_audits",
        "content_documents",
        "content_processing_runs",
        "curriculum_nodes",
        "content_blocks",
    }.issubset(set(inspector.get_table_names()))

    with get_engine().connect() as connection:
        vector_enabled = connection.execute(
            text(
                "SELECT EXISTS "
                "(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
        ).scalar_one()
    assert vector_enabled is True
