from __future__ import annotations

from services.intelligence.projections import (
    EmbeddingRouteIdentity,
    cosine_similarity,
    projection_refresh_generation_key,
    state_representation,
)


def test_state_projection_representation_is_canonical_and_route_identity_is_exact() -> None:
    """Catches a projection becoming comparable across a different embedding route."""

    representation = state_representation(
        subject="MATH",
        concept_ref="long-division",
        state_type="active_difficulty",
        detail="Recent validated evidence shows this concept currently needs support.",
    )
    assert representation.text == (
        "li-state-projection-v1\n"
        "subject: MATH\n"
        "concept_ref: long-division\n"
        "state_type: active_difficulty\n"
        "detail: Recent validated evidence shows this concept currently needs support."
    )
    assert EmbeddingRouteIdentity("fixture", "text-embedding-3-small", 1536) != EmbeddingRouteIdentity(
        "other", "text-embedding-3-small", 1536
    )


def test_calibration_similarity_rejects_incompatible_vectors() -> None:
    """Catches calibration accidentally comparing vectors from incompatible routes."""

    route = EmbeddingRouteIdentity("fixture", "text-embedding-3-small", 3)
    assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0], left_route=route, right_route=route) == 1.0
    assert cosine_similarity(
        [1.0, 0.0, 0.0], [1.0, 0.0, 0.0], left_route=route,
        right_route=EmbeddingRouteIdentity("other", "text-embedding-3-small", 3),
    ) is None


def test_projection_refresh_generation_key_changes_when_embedding_route_changes() -> None:
    """Catches a route change being deduplicated into an old projection job."""

    sources = (("state-id", "representation-hash"),)
    assert projection_refresh_generation_key(
        sources=sources,
        route_identity=EmbeddingRouteIdentity("fixture", "text-embedding-3-small", 1536),
    ) != projection_refresh_generation_key(
        sources=sources,
        route_identity=EmbeddingRouteIdentity("fixture", "another-model", 1536),
    )
