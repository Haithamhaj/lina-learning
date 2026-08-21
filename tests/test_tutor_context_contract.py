"""Small guard that the Tutor context boundary remains a dedicated module."""

from pathlib import Path


def test_tutor_context_builder_module_exists() -> None:
    assert (Path(__file__).parents[1] / "services/tutor/context.py").exists()
