"""PostgreSQL integration tests for the task-routed Model Gateway."""

from __future__ import annotations

import logging
import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

import services.model_gateway.gateway as gateway_module
from services.model_gateway import (
    AIExecutionLineage,
    ModelGateway,
    ModelResult,
    ModelRoute,
    ModelTask,
    StaticModelProvider,
)
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import AIExecution

PRIOR_REVISION = "d7c3b9a5e1f2"
METRIC_COLUMNS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_tokens",
    "output_tokens",
    "latency_ms",
)


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Model Gateway tests",
)


@pytest.fixture(autouse=True)
def preserve_observability_logger_state():
    """Keep Alembic's logging reconfiguration local to migration tests."""

    logger = logging.getLogger("services.platform.observability.metrics")
    was_disabled = logger.disabled
    try:
        yield
    finally:
        logger.disabled = was_disabled


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE ai_executions CASCADE"))
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def test_gateway_executes_by_task_and_persists_usage_latency_and_success(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    route = ModelRoute(provider="mock", model="fixture-tutor")
    provider = StaticModelProvider(
        ModelResult(
            output={"text": "Let us compare the two fractions."},
            input_tokens=12,
            cached_input_tokens=3,
            cache_write_tokens=2,
            output_tokens=9,
            estimated_cost_usd=0.0002,
        )
    )

    with postgres_session_factory.begin() as session:
        result = ModelGateway(
            session,
            routes={ModelTask.TUTOR: route},
            providers={"mock": provider},
        ).execute(ModelTask.TUTOR, {"message": "Are 1/2 and 2/4 equal?"})

    assert result.output["text"].startswith("Let us compare")
    with postgres_session_factory() as session:
        execution = session.query(AIExecution).one()
        assert execution.task == ModelTask.TUTOR.value
        assert execution.provider == "mock"
        assert execution.model == "fixture-tutor"
        assert execution.input_tokens == 12
        assert execution.cached_input_tokens == 3
        assert execution.cache_write_tokens == 2
        assert execution.output_tokens == 9
        assert execution.latency_ms >= 0
        assert execution.estimated_cost_usd == 0.0002
        assert execution.success is True
        assert execution.failure_code is None


def test_gateway_persists_large_responses_usage_and_latency(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real Responses usage and latency can legitimately exceed SMALLINT."""

    clock = iter((100.0, 148.001))
    monkeypatch.setattr(gateway_module, "perf_counter", lambda: next(clock))
    provider = StaticModelProvider(
        ModelResult(
            output={"text": "large usage fixture"},
            input_tokens=48_001,
            cached_input_tokens=48_002,
            cache_write_tokens=48_003,
            output_tokens=48_004,
        )
    )

    with postgres_session_factory.begin() as session:
        ModelGateway(
            session,
            routes={ModelTask.TUTOR: ModelRoute("mock", "fixture-large-usage")},
            providers={"mock": provider},
        ).execute(ModelTask.TUTOR, {"message": "fixture"})

    with postgres_session_factory() as session:
        execution = session.query(AIExecution).one()
        assert execution.input_tokens == 48_001
        assert execution.cached_input_tokens == 48_002
        assert execution.cache_write_tokens == 48_003
        assert execution.output_tokens == 48_004
        assert execution.latency_ms == 48_001


def test_gateway_persists_large_failure_latency_without_changing_error_behavior(
    postgres_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingProvider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route, payload
            raise RuntimeError("fixture failure")

    clock = iter((200.0, 248.002))
    monkeypatch.setattr(gateway_module, "perf_counter", lambda: next(clock))

    with postgres_session_factory.begin() as session:
        gateway = ModelGateway(
            session,
            routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-failure")},
            providers={"fixture": FailingProvider()},
        )
        with pytest.raises(RuntimeError, match="fixture failure"):
            gateway.execute(ModelTask.TUTOR, {"message": "fixture"})

    with postgres_session_factory() as session:
        execution = session.query(AIExecution).one()
        assert execution.success is False
        assert execution.failure_code == "RuntimeError"
        assert execution.latency_ms == 48_002


def test_ai_execution_capacity_migration_round_trips_in_range_values(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    config = Config("alembic.ini")
    engine = postgres_session_factory.kw["bind"]
    assert engine is not None
    execution_id = uuid4()
    values = (31_001, 31_002, 31_003, 31_004, 31_005)

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO ai_executions "
                    "(id, task, provider, model, input_tokens, cached_input_tokens, "
                    "cache_write_tokens, output_tokens, latency_ms, success) "
                    "VALUES (:id, 'tutor', 'fixture', 'fixture', :input_tokens, "
                    ":cached_input_tokens, :cache_write_tokens, :output_tokens, "
                    ":latency_ms, true)"
                ),
                {
                    "id": execution_id,
                    **dict(zip(METRIC_COLUMNS, values, strict=True)),
                },
            )

        command.downgrade(config, PRIOR_REVISION)
        prior_columns = {
            column["name"]: str(column["type"])
            for column in inspect(engine).get_columns("ai_executions")
        }
        assert {prior_columns[name] for name in METRIC_COLUMNS} == {"SMALLINT"}
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT input_tokens, cached_input_tokens, cache_write_tokens, "
                    "output_tokens, latency_ms FROM ai_executions WHERE id = :id"
                ),
                {"id": execution_id},
            ).one() == values

        command.upgrade(config, "head")
        current_columns = {
            column["name"]: str(column["type"])
            for column in inspect(engine).get_columns("ai_executions")
        }
        assert {current_columns[name] for name in METRIC_COLUMNS} == {"INTEGER"}
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT input_tokens, cached_input_tokens, cache_write_tokens, "
                    "output_tokens, latency_ms FROM ai_executions WHERE id = :id"
                ),
                {"id": execution_id},
            ).one() == values
    finally:
        command.upgrade(config, "head")


def test_ai_execution_capacity_migration_refuses_lossy_downgrade(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    config = Config("alembic.ini")
    engine = postgres_session_factory.kw["bind"]
    assert engine is not None
    execution_id = uuid4()
    values = (48_001, 48_002, 48_003, 48_004, 48_005)

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO ai_executions "
                    "(id, task, provider, model, input_tokens, cached_input_tokens, "
                    "cache_write_tokens, output_tokens, latency_ms, success) "
                    "VALUES (:id, 'tutor', 'fixture', 'fixture', :input_tokens, "
                    ":cached_input_tokens, :cache_write_tokens, :output_tokens, "
                    ":latency_ms, true)"
                ),
                {
                    "id": execution_id,
                    **dict(zip(METRIC_COLUMNS, values, strict=True)),
                },
            )

        with pytest.raises(RuntimeError, match="outside the signed SMALLINT range"):
            command.downgrade(config, PRIOR_REVISION)

        current_columns = {
            column["name"]: str(column["type"])
            for column in inspect(engine).get_columns("ai_executions")
        }
        assert {current_columns[name] for name in METRIC_COLUMNS} == {"INTEGER"}
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT input_tokens, cached_input_tokens, cache_write_tokens, "
                    "output_tokens, latency_ms FROM ai_executions WHERE id = :id"
                ),
                {"id": execution_id},
            ).one() == values
    finally:
        command.upgrade(config, "head")


def test_gateway_route_can_change_without_changing_the_caller(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    provider = StaticModelProvider(ModelResult(output={"text": "ok"}))

    with postgres_session_factory.begin() as session:
        gateway = ModelGateway(
            session,
            routes={ModelTask.CURRICULUM_SEMANTICS: ModelRoute("mock", "first")},
            providers={"mock": provider},
        )
        gateway.execute(ModelTask.CURRICULUM_SEMANTICS, {"source": "fixture"})
        gateway.set_route(
            ModelTask.CURRICULUM_SEMANTICS,
            ModelRoute("mock", "second"),
        )
        gateway.execute(ModelTask.CURRICULUM_SEMANTICS, {"source": "fixture"})

    with postgres_session_factory() as session:
        assert [row.model for row in session.query(AIExecution).order_by(AIExecution.created_at)] == [
            "first",
            "second",
        ]


def test_gateway_records_identifier_only_lineage_and_separate_retry_attempts(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    operation_id = uuid4()
    with postgres_session_factory.begin() as session:
        gateway = ModelGateway(
            session,
            routes={ModelTask.TUTOR: ModelRoute("mock", "fixture")},
            providers={"mock": StaticModelProvider(ModelResult(output={"text": "ok"}))},
        )
        first = gateway.execute(
            ModelTask.TUTOR,
            {"input": "not persisted in lineage"},
            lineage=AIExecutionLineage(
                operation="tutor_turn",
                operation_id=operation_id,
            ),
        )
        second = gateway.execute(
            ModelTask.TUTOR,
            {"input": "retry"},
            lineage=AIExecutionLineage(
                operation="tutor_turn",
                operation_id=operation_id,
                parent_execution_id=first.execution_id,
            ),
        )
        rows = session.query(AIExecution).filter_by(operation_id=operation_id).order_by(AIExecution.created_at, AIExecution.id).all()

    assert first.execution_id != second.execution_id
    assert all(row.operation_id == operation_id for row in rows)
    second_row = next(row for row in rows if row.id == second.execution_id)
    assert second_row.parent_execution_id == first.execution_id
    assert all(row.source_message_id is None for row in rows)
    assert all(row.source_candidate_event_ids == [] for row in rows)


def test_failed_attempt_is_preserved_before_an_explicit_retry(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    class FailingProvider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route, payload
            raise RuntimeError("fixture failure")

    operation_id = uuid4()
    with postgres_session_factory.begin() as session:
        failing = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "first")},
            providers={"fixture": FailingProvider()},
        )
        with pytest.raises(RuntimeError, match="fixture failure"):
            failing.execute(
                ModelTask.SESSION_EVIDENCE,
                {},
                lineage=AIExecutionLineage(operation="session_evidence_consolidation", operation_id=operation_id),
            )
        failed = session.query(AIExecution).one()
        retry = ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("fixture", "second")},
            providers={"fixture": StaticModelProvider(ModelResult(output={}))},
        ).execute(
            ModelTask.SESSION_EVIDENCE,
            {},
            lineage=AIExecutionLineage(
                operation="session_evidence_consolidation",
                operation_id=operation_id,
                parent_execution_id=failed.id,
            ),
        )
        attempts = session.query(AIExecution).filter_by(operation_id=operation_id).order_by(AIExecution.created_at, AIExecution.id).all()

    failed_row = next(attempt for attempt in attempts if attempt.id == failed.id)
    retry_row = next(attempt for attempt in attempts if attempt.id == retry.execution_id)
    assert {attempt.success for attempt in attempts} == {False, True}
    assert failed_row.failure_code == "RuntimeError"
    assert retry_row.parent_execution_id == failed.id
