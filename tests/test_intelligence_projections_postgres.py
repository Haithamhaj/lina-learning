"""PostgreSQL contracts for retrieval-only Learning Intelligence projections."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.current_state import CURRENT_STATE_POLICY_VERSION
from services.intelligence.projections import refresh_projection_batch, state_source_representation
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CurrentLearningState,
    CurrentLearningStateProjection,
    IntelligenceProcessingRun,
    ModelTask,
    Student,
    User,
)


pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL required")


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE ai_executions, jobs, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _state(session: Session) -> CurrentLearningState:
    user = User(identity_provider="fixture", external_subject=uuid4().hex, role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id)
    session.add(student)
    session.flush()
    run = IntelligenceProcessingRun(student_id=student.id, rubric_version="fixture", policy_version="fixture", scope={})
    session.add(run)
    session.flush()
    state = CurrentLearningState(
        student_id=student.id,
        processing_run_id=run.id,
        subject="MATH",
        state_type="active_difficulty",
        concept_ref="long-division",
        detail="Long division needs support.",
        status="ACTIVE",
        evidence_refs=[],
        policy_version=CURRENT_STATE_POLICY_VERSION,
    )
    session.add(state)
    session.flush()
    return state


def _gateway(session: Session, *, provider: str = "fixture", model: str = "text-embedding-3-small") -> ModelGateway:
    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            return ModelResult(output={"embeddings": [[1.0] + [0.0] * 1535 for _ in payload["input"]]})

    return ModelGateway(session, routes={ModelTask.EMBEDDING: ModelRoute(provider, model)}, providers={provider: Provider()})


def test_projection_refresh_is_idempotent_rejects_stale_revision_and_cascades(factory: sessionmaker[Session]) -> None:
    """Catches a stale vector being written or surviving deletion of its authority source."""

    with factory.begin() as session:
        state = _state(session)
        payload = {
            "student_id": str(state.student_id),
            "states": [{"id": str(state.id), "hash": state_source_representation(state).hash}],
            "patterns": [],
            "route_identity": {"provider": "fixture", "model": "text-embedding-3-small", "dimensions": 1536},
        }
        assert refresh_projection_batch(session, payload=payload, gateway=_gateway(session)) == {"refreshed": 1, "obsolete": 0}
        assert refresh_projection_batch(session, payload=payload, gateway=_gateway(session)) == {"refreshed": 1, "obsolete": 0}
        assert session.query(CurrentLearningStateProjection).count() == 1
        state.detail = "Changed authoritative meaning."
        assert refresh_projection_batch(session, payload=payload, gateway=_gateway(session)) == {"refreshed": 0, "obsolete": 0}
        session.delete(state)
        session.flush()
        assert session.query(CurrentLearningStateProjection).count() == 0


def test_projection_refresh_route_mismatch_is_a_safe_noop(factory: sessionmaker[Session]) -> None:
    """Catches an old queued route silently being executed through a new route."""

    with factory.begin() as session:
        state = _state(session)
        payload = {
            "student_id": str(state.student_id),
            "states": [{"id": str(state.id), "hash": state_source_representation(state).hash}],
            "patterns": [],
            "route_identity": {"provider": "old-provider", "model": "old-model", "dimensions": 1536},
        }
        assert refresh_projection_batch(session, payload=payload, gateway=_gateway(session)) == {"refreshed": 0, "obsolete": 1}
        assert session.query(CurrentLearningStateProjection).count() == 0
