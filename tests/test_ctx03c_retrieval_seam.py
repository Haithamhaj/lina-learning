"""CTX-03C contracts for an explicitly supplied or unavailable query vector."""

from __future__ import annotations

from services.retrieval.service import QueryEmbedding


def test_query_embedding_states_distinguish_not_supplied_from_unavailable() -> None:
    """Catches a hidden second embedding request after conversation embedding failed."""

    assert QueryEmbedding.not_supplied().allows_generation is True
    assert QueryEmbedding.unavailable().allows_generation is False
    assert QueryEmbedding.available([0.0] * 1536).vector == [0.0] * 1536
