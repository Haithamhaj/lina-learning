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
        "document_structural_items",
        "content_semantic_processing_runs",
        "content_semantic_items",
        "content_semantic_item_sources",
        "content_index_runs",
        "indexed_content_blocks",
        "indexed_content_block_sources",
        "curriculum_nodes",
        "content_blocks",
        "learning_sessions",
        "learning_segments",
        "segment_learning_reviews",
        "learning_messages",
        "learning_exchange_embeddings",
        "candidate_events",
        "intelligence_processing_runs",
        "intelligence_reprocess_runs",
        "intelligence_reprocess_sessions",
        "intelligence_session_authorities",
        "learning_events",
        "learning_evidence",
        "current_learning_states",
        "learner_patterns",
        "pattern_evidence",
        "learner_intelligence_cards",
            "decision_views",
            "personal_facts",
            "personal_fact_observations",
            "personal_fact_extraction_runs",
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
        "document_structural_items",
        "content_semantic_processing_runs",
        "content_semantic_items",
        "content_semantic_item_sources",
        "content_index_runs",
        "indexed_content_blocks",
        "indexed_content_block_sources",
        "curriculum_nodes",
        "content_blocks",
        "learning_sessions",
        "learning_segments",
        "learning_messages",
        "candidate_events",
        "intelligence_processing_runs",
        "learning_events",
        "learning_evidence",
        "current_learning_states",
        "learner_patterns",
        "pattern_evidence",
        "learner_intelligence_cards",
        "decision_views",
    }.issubset(set(inspector.get_table_names()))

    with get_engine().connect() as connection:
        vector_enabled = connection.execute(
            text(
                "SELECT EXISTS "
                "(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
        ).scalar_one()
    assert vector_enabled is True
