"""Retrieval-only semantic projections for authoritative learning intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from math import sqrt
from typing import Iterable
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.db.models import (
    CurrentLearningState,
    CurrentLearningStateProjection,
    LearnerPattern,
    LearnerPatternProjection,
    ModelTask,
)
from services.platform.jobs import enqueue_job
from services.intelligence.current_state import CURRENT_STATE_POLICY_VERSION
from services.intelligence.patterns import PATTERN_POLICY_VERSION
from services.platform.config import get_settings


STATE_PROJECTION_REPRESENTATION_VERSION = "li-state-projection-v1"
PATTERN_PROJECTION_REPRESENTATION_VERSION = "li-pattern-projection-v1"
LEARNING_INTELLIGENCE_PROJECTION_REFRESH_JOB = "LEARNING_INTELLIGENCE_PROJECTION_REFRESH"


@dataclass(frozen=True)
class EmbeddingRouteIdentity:
    """The complete identity required before two vectors may be compared."""

    provider: str
    model: str
    dimensions: int

    def __post_init__(self) -> None:
        if not self.provider or not self.model or self.dimensions <= 0:
            raise ValueError("Embedding route identity must be complete.")


@dataclass(frozen=True)
class CanonicalRepresentation:
    version: str
    text: str
    hash: str


def state_representation(
    *, subject: str, concept_ref: str | None, state_type: str, detail: str
) -> CanonicalRepresentation:
    return _representation(
        STATE_PROJECTION_REPRESENTATION_VERSION,
        (
            ("subject", subject),
            ("concept_ref", concept_ref or "none"),
            ("state_type", state_type),
            ("detail", detail),
        ),
    )


def pattern_representation(
    *,
    subject: str,
    scope_type: str,
    concept_ref: str | None,
    context_ref: str | None,
    pattern_type: str,
    pattern_key: str,
    detail: str,
) -> CanonicalRepresentation:
    return _representation(
        PATTERN_PROJECTION_REPRESENTATION_VERSION,
        (
            ("subject", subject),
            ("scope_type", scope_type),
            ("concept_ref", concept_ref or "none"),
            ("context_ref", context_ref or "none"),
            ("pattern_type", pattern_type),
            ("pattern_key", pattern_key),
            ("detail", detail),
        ),
    )


def _representation(version: str, fields: tuple[tuple[str, str], ...]) -> CanonicalRepresentation:
    text = "\n".join((version, *(f"{key}: {value}" for key, value in fields)))
    return CanonicalRepresentation(version=version, text=text, hash=sha256(text.encode()).hexdigest())


def state_source_representation(source: CurrentLearningState) -> CanonicalRepresentation:
    return state_representation(
        subject=source.subject,
        concept_ref=source.concept_ref,
        state_type=source.state_type,
        detail=source.detail,
    )


def pattern_source_representation(source: LearnerPattern) -> CanonicalRepresentation:
    scope = source.scope if isinstance(source.scope, dict) else {}
    return pattern_representation(
        subject=str(scope.get("subject") or "none"),
        scope_type=str(scope.get("scope_type") or "concept"),
        concept_ref=_optional_scope_value(scope, "concept_ref"),
        context_ref=_optional_scope_value(scope, "context_ref"),
        pattern_type=source.pattern_type,
        pattern_key=source.pattern_key,
        detail=source.detail,
    )


def enqueue_projection_refresh(
    session: Session,
    *,
    student_id: UUID,
    states: Iterable[CurrentLearningState] = (),
    patterns: Iterable[LearnerPattern] = (),
) -> None:
    """Commit a disposable refresh request alongside an authority mutation."""

    state_items = [
        {"id": str(source.id), "hash": state_source_representation(source).hash}
        for source in states
    ]
    pattern_items = [
        {"id": str(source.id), "hash": pattern_source_representation(source).hash}
        for source in patterns
    ]
    if not state_items and not pattern_items:
        return
    route_identity = configured_embedding_route_identity()
    digest = projection_refresh_generation_key(
        sources=tuple((item["id"], item["hash"]) for item in (*state_items, *pattern_items)),
        route_identity=route_identity,
    )
    enqueue_job(
        session,
        job_type=LEARNING_INTELLIGENCE_PROJECTION_REFRESH_JOB,
        payload={
            "student_id": str(student_id),
            "states": state_items,
            "patterns": pattern_items,
            "route_identity": _route_payload(route_identity),
        },
        idempotency_key=f"li-projection-refresh:{student_id}:{digest}",
    )


def enqueue_eligible_projection_backfill(session: Session, *, student_id: UUID) -> None:
    """Queue projections for existing eligible sources without touching authority."""

    states = session.scalars(select(CurrentLearningState).where(
        CurrentLearningState.student_id == student_id,
        CurrentLearningState.status == "ACTIVE",
        CurrentLearningState.policy_version == CURRENT_STATE_POLICY_VERSION,
        CurrentLearningState.state_type != "current_school_focus",
        or_(CurrentLearningState.expires_at.is_(None), CurrentLearningState.expires_at > datetime.now(UTC)),
    )).all()
    patterns = [
        row for row in session.scalars(select(LearnerPattern).where(
            LearnerPattern.student_id == student_id,
            LearnerPattern.policy_version == PATTERN_POLICY_VERSION,
            LearnerPattern.status.in_(("ACTIVE", "STABLE")),
        )).all()
        if isinstance(row.scope, dict) and isinstance(row.scope.get("subject"), str)
    ]
    enqueue_projection_refresh(session, student_id=student_id, states=states, patterns=patterns)


def refresh_projection_batch(session: Session, *, payload: dict[str, object], gateway: ModelGateway) -> dict[str, int]:
    """Refresh only source revisions still matching the committed job payload."""

    student_id = UUID(str(payload["student_id"]))
    route = gateway.route_for(ModelTask.EMBEDDING)
    identity = EmbeddingRouteIdentity(route.provider, route.model, 1536)
    expected_identity = _route_from_payload(payload.get("route_identity"))
    if expected_identity is None:
        raise ValueError("Projection refresh route identity is required.")
    if expected_identity != identity:
        return {"refreshed": 0, "obsolete": _requested_count(payload)}
    sources: list[tuple[str, object, CanonicalRepresentation]] = []
    for source in _requested_states(session, student_id=student_id, values=payload.get("states")):
        sources.append(("state", source, state_source_representation(source)))
    for source in _requested_patterns(session, student_id=student_id, values=payload.get("patterns")):
        sources.append(("pattern", source, pattern_source_representation(source)))
    if not sources:
        return {"refreshed": 0, "obsolete": 0}
    result = gateway.execute(
        ModelTask.EMBEDDING,
        {"input": [representation.text for _, _, representation in sources], "dimensions": identity.dimensions},
        lineage=AIExecutionLineage(operation="learning_intelligence_projection_refresh", student_id=student_id),
    )
    vectors = result.output.get("embeddings")
    if not isinstance(vectors, list) or len(vectors) != len(sources):
        raise ValueError("Projection embedding result count is invalid.")
    for (kind, source, representation), vector in zip(sources, vectors, strict=True):
        if not isinstance(vector, list) or len(vector) != identity.dimensions:
            raise ValueError("Projection embedding dimensions are invalid.")
        _upsert_projection(
            session=session,
            kind=kind,
            source=source,
            representation=representation,
            identity=identity,
            embedding=[float(value) for value in vector],
            ai_execution_id=result.execution_id,
        )
    return {"refreshed": len(sources), "obsolete": 0}


def _requested_states(session: Session, *, student_id: UUID, values: object) -> list[CurrentLearningState]:
    requested = _requested_hashes(values)
    if not requested:
        return []
    rows = session.scalars(select(CurrentLearningState).where(CurrentLearningState.id.in_(requested), CurrentLearningState.student_id == student_id)).all()
    return [row for row in rows if state_source_representation(row).hash == requested[row.id]]


def _requested_patterns(session: Session, *, student_id: UUID, values: object) -> list[LearnerPattern]:
    requested = _requested_hashes(values)
    if not requested:
        return []
    rows = session.scalars(select(LearnerPattern).where(LearnerPattern.id.in_(requested), LearnerPattern.student_id == student_id)).all()
    return [row for row in rows if pattern_source_representation(row).hash == requested[row.id]]


def _requested_hashes(values: object) -> dict[UUID, str]:
    if not isinstance(values, list):
        return {}
    result: dict[UUID, str] = {}
    for item in values:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("hash"), str):
            continue
        try:
            result[UUID(item["id"])] = item["hash"]
        except ValueError:
            continue
    return result


def configured_embedding_route_identity() -> EmbeddingRouteIdentity:
    """Mirror the configured ModelTask.EMBEDDING route without making a request."""

    settings = get_settings()
    provider = "openai" if settings.model_provider == "openai" else "local-demo"
    return EmbeddingRouteIdentity(provider, settings.embedding_model_name, settings.embedding_dimensions)


def projection_refresh_generation_key(*, sources: tuple[tuple[str, str], ...], route_identity: EmbeddingRouteIdentity) -> str:
    """Stable job generation identity for source representation plus embedding route."""

    material = (tuple(sorted(sources)), route_identity.provider, route_identity.model, route_identity.dimensions)
    return sha256(repr(material).encode()).hexdigest()


def _route_payload(identity: EmbeddingRouteIdentity) -> dict[str, object]:
    return {"provider": identity.provider, "model": identity.model, "dimensions": identity.dimensions}


def _route_from_payload(value: object) -> EmbeddingRouteIdentity | None:
    if not isinstance(value, dict):
        return None
    provider, model, dimensions = value.get("provider"), value.get("model"), value.get("dimensions")
    if not isinstance(provider, str) or not isinstance(model, str) or not isinstance(dimensions, int):
        return None
    return EmbeddingRouteIdentity(provider, model, dimensions)


def _requested_count(payload: dict[str, object]) -> int:
    return len(_requested_hashes(payload.get("states"))) + len(_requested_hashes(payload.get("patterns")))


def _upsert_projection(*, session: Session, kind: str, source: object, representation: CanonicalRepresentation, identity: EmbeddingRouteIdentity, embedding: list[float], ai_execution_id: UUID | None) -> None:
    if kind == "state":
        source_id = source.id  # type: ignore[union-attr]
        row = session.scalar(select(CurrentLearningStateProjection).where(
            CurrentLearningStateProjection.current_learning_state_id == source_id,
            CurrentLearningStateProjection.representation_version == representation.version,
            CurrentLearningStateProjection.embedding_provider == identity.provider,
            CurrentLearningStateProjection.embedding_model == identity.model,
            CurrentLearningStateProjection.dimensions == identity.dimensions,
        ))
        if row is None:
            session.add(CurrentLearningStateProjection(current_learning_state_id=source_id, embedding=embedding, embedding_provider=identity.provider, embedding_model=identity.model, dimensions=identity.dimensions, representation_version=representation.version, representation_hash=representation.hash, ai_execution_id=ai_execution_id))
        else:
            row.embedding, row.representation_hash, row.ai_execution_id = embedding, representation.hash, ai_execution_id
        return
    source_id = source.id  # type: ignore[union-attr]
    row = session.scalar(select(LearnerPatternProjection).where(
        LearnerPatternProjection.learner_pattern_id == source_id,
        LearnerPatternProjection.representation_version == representation.version,
        LearnerPatternProjection.embedding_provider == identity.provider,
        LearnerPatternProjection.embedding_model == identity.model,
        LearnerPatternProjection.dimensions == identity.dimensions,
    ))
    if row is None:
        session.add(LearnerPatternProjection(learner_pattern_id=source_id, embedding=embedding, embedding_provider=identity.provider, embedding_model=identity.model, dimensions=identity.dimensions, representation_version=representation.version, representation_hash=representation.hash, ai_execution_id=ai_execution_id))
    else:
        row.embedding, row.representation_hash, row.ai_execution_id = embedding, representation.hash, ai_execution_id


def _optional_scope_value(scope: dict[str, object], key: str) -> str | None:
    value = scope.get(key)
    return value if isinstance(value, str) and value else None


def cosine_similarity(
    left: list[float], right: list[float], *, left_route: EmbeddingRouteIdentity, right_route: EmbeddingRouteIdentity
) -> float | None:
    """Read-only calibration helper; never compare vectors across routes."""

    if left_route != right_route or len(left) != left_route.dimensions or len(right) != right_route.dimensions:
        return None
    denominator = sqrt(sum(value * value for value in left)) * sqrt(sum(value * value for value in right))
    return None if denominator == 0 else sum(a * b for a, b in zip(left, right, strict=True)) / denominator
