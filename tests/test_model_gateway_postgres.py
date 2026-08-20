"""PostgreSQL integration tests for the task-routed Model Gateway."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.model_gateway import (
    ModelGateway,
    ModelResult,
    ModelRoute,
    ModelTask,
    StaticModelProvider,
)
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import AIExecution


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Model Gateway tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE ai_executions"))
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
        assert execution.output_tokens == 9
        assert execution.latency_ms >= 0
        assert execution.estimated_cost_usd == 0.0002
        assert execution.success is True
        assert execution.failure_code is None


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
