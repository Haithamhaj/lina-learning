"""Unit tests for the OpenAI Model Gateway adapter."""

from __future__ import annotations

import importlib
import json

from services.model_gateway.factory import create_tutor_gateway
from services.model_gateway.gateway import ModelResult, ModelRoute, StaticModelProvider
from services.model_gateway.openai_provider import OpenAIResponsesProvider
from services.platform.config import Settings
from services.platform.db.models import ModelTask


def test_tutor_runtime_exposes_a_provider_neutral_model_payload() -> None:
    """Tutor supplies grounding and compact context without knowing the provider."""

    module = importlib.import_module("services.tutor.runtime")
    assert hasattr(module, "build_tutor_model_payload")
    payload = module.build_tutor_model_payload(
        question="How does 4.2 × 10 change the decimal point?",
        sources=[{"ref": "Eureka#page=16", "text": "Use a place value chart."}],
        intelligence=["Recent support need: place value × 10."],
    )

    assert payload["max_output_tokens"] == 350
    assert payload["instructions"] == module.TUTOR_SHARED_INSTRUCTIONS
    assert "4.2 × 10" not in payload["instructions"]
    assert "Eureka#page=16" not in payload["instructions"]
    assert "Recent support need" not in payload["instructions"]
    assert "Eureka#page=16" in payload["input"]
    assert "Recent support need" in payload["input"]
    assert "internal policies" in payload["instructions"]
    assert "Sandbox/Test Learner" not in payload["instructions"]


def test_openai_responses_provider_returns_text_usage_and_luna_cost() -> None:
    """The adapter normalizes one Responses API result without exposing a key."""

    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "Try one step at a time."}],
                        }
                    ],
                    "usage": {"input_tokens": 392, "output_tokens": 143},
                }
            ).encode()

    def send(request: object, *, timeout: float) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    provider = OpenAIResponsesProvider(api_key="test-key", request_sender=send)
    result = provider.execute(
        ModelRoute(provider="openai", model="gpt-5.6-luna"),
        {"instructions": "Teach calmly.", "input": "Help with 4.2 × 10."},
    )

    request = captured["request"]
    body = json.loads(request.data.decode())
    assert request.full_url == "https://api.openai.com/v1/responses"
    assert body == {
        "model": "gpt-5.6-luna",
        "instructions": "Teach calmly.",
        "input": "Help with 4.2 × 10.",
        "store": False,
    }
    assert result.output == {"text": "Try one step at a time."}
    assert result.input_tokens == 392
    assert result.cached_input_tokens == 0
    assert result.output_tokens == 143
    assert result.estimated_cost_usd == 0.000625


def test_openai_responses_provider_accounts_for_each_luna_prompt_cache_category() -> None:
    """Responses usage keeps normal reads, cache reads, and writes distinct."""

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "Try it."}],
                        }
                    ],
                    "usage": {
                        "input_tokens": 1000,
                        "input_tokens_details": {"cached_tokens": 400, "cache_write_tokens": 200},
                        "output_tokens": 100,
                    },
                }
            ).encode()

    def send(request: object, *, timeout: float) -> FakeResponse:
        del request, timeout
        return FakeResponse()

    result = OpenAIResponsesProvider(api_key="test-key", request_sender=send).execute(
        ModelRoute(provider="openai", model="gpt-5.6-luna"),
        {"instructions": "Teach calmly.", "input": "Help with 4.2 × 10."},
    )

    # (400 × $0.50 + 400 × $0.05 + 200 × $0.625 + 100 × $3.00) / 1,000,000
    assert result.input_tokens == 400
    assert result.cached_input_tokens == 400
    assert result.cache_write_tokens == 200
    assert result.output_tokens == 100
    assert result.estimated_cost_usd == 0.000645


def test_tutor_gateway_uses_openai_route_from_settings() -> None:
    """A configured OpenAI Tutor call records its configured provider and model."""

    class RecordingSession:
        def __init__(self) -> None:
            self.rows: list[object] = []

        def add(self, row: object) -> None:
            self.rows.append(row)

        def flush(self) -> None:
            return None

    settings = Settings(
        _env_file=None,
        model_provider="openai",
        model_name="gpt-5.6-luna",
        model_api_key="test-key",
    )
    session = RecordingSession()
    gateway = create_tutor_gateway(
        session,
        settings=settings,
        openai_provider=StaticModelProvider(
            ModelResult(
                output={"text": "Try one digit at a time."},
                input_tokens=10,
                cached_input_tokens=4,
                cache_write_tokens=2,
                output_tokens=6,
            )
        ),
    )

    gateway.execute(ModelTask.TUTOR, {"instructions": "Teach calmly.", "input": "Help with 4.2 × 10."})

    execution = session.rows[0]
    assert execution.provider == "openai"
    assert execution.model == "gpt-5.6-luna"
    assert execution.input_tokens == 10
    assert execution.cached_input_tokens == 4
    assert execution.cache_write_tokens == 2
    assert execution.output_tokens == 6
