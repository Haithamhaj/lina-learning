"""Small guard that the Tutor context boundary remains a dedicated module."""

from pathlib import Path

from services.tutor import context
from services.tutor.context import TutorContextBuilder


def test_tutor_context_builder_module_exists() -> None:
    assert (Path(__file__).parents[1] / "services/tutor/context.py").exists()


def test_default_context_builder_constructs_hybrid_retrieval_with_embedding_gateway(
    monkeypatch,
) -> None:
    gateway = object()
    monkeypatch.setattr(context, "create_embedding_gateway", lambda session: gateway, raising=False)

    builder = TutorContextBuilder(object())

    assert builder._retrieval._embedding_gateway is gateway
