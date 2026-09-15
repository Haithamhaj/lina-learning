from __future__ import annotations

from services.intelligence.projections import (
    EmbeddingRouteIdentity,
    cosine_similarity,
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
