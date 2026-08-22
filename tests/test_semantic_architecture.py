"""Guard the TASK-012 model-boundary and semantic-meaning architecture."""

from pathlib import Path


def test_content_semantics_uses_only_the_model_gateway_boundary() -> None:
    source = Path("services/content/semantics.py").read_text()

    assert "gateway.execute(" in source
    assert "ModelTask.CURRICULUM_SEMANTICS" in source
    assert "OpenAI" not in source
    assert "urlopen" not in source
    assert "requests." not in source
    assert "import re" not in source
