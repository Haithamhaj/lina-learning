"""Unit tests for the OpenAI Model Gateway adapter."""

from __future__ import annotations

import importlib
import json

import pytest

from services.model_gateway.factory import create_tutor_gateway
from services.model_gateway.gateway import ModelResult, ModelRoute, StaticModelProvider, StreamComplete, StreamDelta, StreamParentBoundaryDecision
from services.model_gateway.openai_provider import OpenAIResponsesProvider
from services.platform.config import Settings, reset_settings_cache
from services.platform.db.models import ModelTask
from services.tutor.candidate_events import TUTOR_OUTPUT_RESPONSE_SCHEMA


def _v9_tutor_payload_without_workspace_intent() -> dict[str, object]:
    return {
        "instructions": "Teach calmly.",
        "input": "Help with fractions.",
        "response_schema": TUTOR_OUTPUT_RESPONSE_SCHEMA,
    }


def _v9_tutor_body_without_workspace_intent() -> str:
    return json.dumps({
        "text": "Try one step.",
        "suggested_actions": [],
        "guided_check": None,
        "teaching_mode": None,
        "teaching_strategy": None,
        "teaching_method_id": None,
        "prior_method_relation": None,
        "segment_relation": None,
        "structured_segment_state": None,
        "parent_boundary": None,
        "candidate_metadata": None,
        "provisional_broad_subject": None,
    })


def test_tutor_runtime_exposes_a_provider_neutral_model_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tutor supplies grounding and compact context without knowing the provider."""

    monkeypatch.setenv("TUTOR_MAX_OUTPUT_TOKENS", "2400")
    reset_settings_cache()
    try:
        module = importlib.import_module("services.tutor.runtime")
        assert hasattr(module, "build_tutor_model_payload")
        payload = module.build_tutor_model_payload(
            question="How does 4.2 × 10 change the decimal point?",
            sources=[{"ref": "Eureka#page=16", "text": "Use a place value chart."}],
            intelligence=["Recent support need: place value × 10."],
            safety_directive="Use simple framing and avoid adult-level detail.",
        )
    finally:
        reset_settings_cache()

    assert payload["max_output_tokens"] == 2400
    assert payload["instructions"] == module.TUTOR_SHARED_INSTRUCTIONS
    assert "4.2 × 10" not in payload["instructions"]
    assert "Eureka#page=16" not in payload["instructions"]
    assert "Recent support need" not in payload["instructions"]
    assert "Eureka#page=16" in payload["input"]
    assert "Recent support need" in payload["input"]
    assert "Use simple framing and avoid adult-level detail." in payload["input"]
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


def test_openai_execute_rejects_v9_result_without_required_workspace_intent() -> None:
    """A completed strict v9 response cannot be normalized as an ordinary absent intent."""

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({
                "output": [{"type": "message", "content": [{"type": "output_text", "text": _v9_tutor_body_without_workspace_intent()}]}],
                "usage": {"input_tokens": 5, "output_tokens": 2},
            }).encode()

    def send(request: object, *, timeout: float) -> FakeResponse:
        del request, timeout
        return FakeResponse()

    with pytest.raises(ValueError, match="workspace_intent"):
        OpenAIResponsesProvider(api_key="test-key", request_sender=send).execute(
            ModelRoute(provider="openai", model="gpt-5.6-luna"),
            _v9_tutor_payload_without_workspace_intent(),
        )


def test_openai_stream_rejects_v9_result_without_required_workspace_intent() -> None:
    """The streaming completion path enforces the same strict v9 boundary as execute."""

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def __iter__(self):
            return iter([
                f"data: {json.dumps({'type': 'response.output_text.delta', 'delta': _v9_tutor_body_without_workspace_intent()})}\n\n".encode(),
                b'data: {"type":"response.completed","response":{"usage":{"input_tokens":5,"output_tokens":2}}}\n\n',
            ])

    def send(request: object, *, timeout: float) -> FakeResponse:
        del request, timeout
        return FakeResponse()

    with pytest.raises(ValueError, match="workspace_intent"):
        list(
            OpenAIResponsesProvider(api_key="test-key", request_sender=send).stream(
                ModelRoute(provider="openai", model="gpt-5.6-luna"),
                _v9_tutor_payload_without_workspace_intent(),
            )
        )


def test_openai_responses_provider_forwards_real_sse_deltas_from_one_request() -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def __iter__(self):
            return iter(
                [
                    b'data: {"type":"response.output_text.delta","delta":"Try "}\n\n',
                    b'data: {"type":"response.output_text.delta","delta":"this."}\n\n',
                    b'data: {"type":"response.completed","response":{"usage":{"input_tokens":5,"output_tokens":2}}}\n\n',
                ]
            )

    def send(request: object, *, timeout: float) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    events = list(
        OpenAIResponsesProvider(api_key="test-key", request_sender=send).stream(
            ModelRoute(provider="openai", model="gpt-5.6-luna"),
            {"instructions": "Teach calmly.", "input": "Help with fractions."},
        )
    )

    request = captured["request"]
    assert json.loads(request.data.decode())["stream"] is True
    assert request.get_header("Accept") == "text/event-stream"
    assert [event.text for event in events if isinstance(event, StreamDelta)] == ["Try ", "this."]
    assert isinstance(events[-1], StreamComplete)
    assert events[-1].result.output == {"text": "Try this."}


def test_openai_responses_provider_reports_the_reason_for_an_incomplete_stream() -> None:
    """A terminal incomplete Response must not be mistaken for a transport EOF."""

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def __iter__(self):
            return iter(
                [
                    b'data: {"type":"response.output_text.delta","delta":"Try "}\n\n',
                    b'data: {"type":"response.incomplete","response":{"incomplete_details":{"reason":"max_output_tokens"}}}\n\n',
                ]
            )

    def send(request: object, *, timeout: float) -> FakeResponse:
        del request, timeout
        return FakeResponse()

    with pytest.raises(ValueError, match="OpenAI Responses API incomplete: max_output_tokens"):
        list(
            OpenAIResponsesProvider(api_key="test-key", request_sender=send).stream(
                ModelRoute(provider="openai", model="gpt-5.6-luna"),
                {"instructions": "Teach calmly.", "input": "Help with fractions."},
            )
        )


def test_openai_responses_provider_streams_student_text_from_a_structured_tutor_result() -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def __iter__(self):
            return iter(
                [
                    b'data: {"type":"response.output_text.delta","delta":"{\\"text\\":\\"Try "}\n\n',
                    b'data: {"type":"response.output_text.delta","delta":"one step.\\",\\"suggested_actions\\":[{\\"label\\":\\"Let me try \\u270d\\ufe0f\\",\\"kind\\":\\"NAVIGATION\\"}],\\"candidate_metadata\\":{\\"version\\":\\"candidate-event-v1\\",\\"candidates\\":[]}}"}\n\n',
                    b'data: {"type":"response.completed","response":{"usage":{"input_tokens":5,"output_tokens":2}}}\n\n',
                ]
            )

    def send(request: object, *, timeout: float) -> FakeResponse:
        captured["request"] = request
        return FakeResponse()

    events = list(
        OpenAIResponsesProvider(api_key="test-key", request_sender=send).stream(
            ModelRoute(provider="openai", model="gpt-5.6-luna"),
            {
                "instructions": "Teach calmly.",
                "input": "Help with fractions.",
                "response_schema": {"name": "tutor_turn_v3", "schema": {"type": "object"}},
            },
        )
    )

    request = captured["request"]
    body = json.loads(request.data.decode())
    assert body["text"]["format"] == {
        "type": "json_schema", "name": "tutor_turn_v3", "schema": {"type": "object"}, "strict": True,
    }
    assert [event.text for event in events if isinstance(event, StreamDelta)] == ["Try ", "one step."]
    assert events[-1].result.output == {
        "text": "Try one step.",
        "suggested_actions": [{"label": "Let me try ✍️", "kind": "NAVIGATION"}],
        "candidate_metadata": {"version": "candidate-event-v1", "candidates": []},
    }


def test_openai_structured_stream_extracts_parent_decision_after_text_without_key_order_assumption() -> None:
    """SAFE-02: runtime can buffer text until this independent field is complete."""

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def __iter__(self):
            return iter(
                [
                    b'data: {"type":"response.output_text.delta","delta":"{\\"text\\":\\"ordinary reply\\",\\"parent_boundary\\":{\\"schema_version\\":\\"parent-boundary-v1\\",\\"category\\":\\"RELIGION\\",\\"applies\\":true,"}\n\n',
                    b'data: {"type":"response.output_text.delta","delta":"\\"model_action\\":\\"REDIRECT_TO_PARENT\\",\\"redirect\\":null}}"}\n\n',
                    b'data: {"type":"response.completed","response":{"usage":{"input_tokens":5,"output_tokens":2}}}\n\n',
                ]
            )

    def send(request: object, *, timeout: float) -> FakeResponse:
        del request, timeout
        return FakeResponse()

    events = list(
        OpenAIResponsesProvider(api_key="test-key", request_sender=send).stream(
            ModelRoute(provider="openai", model="gpt-5.6-luna"),
            {
                "instructions": "Teach calmly.",
                "input": "Help with fractions.",
                "response_schema": {
                    "name": "tutor_turn_v7",
                    "schema": {"type": "object", "properties": {"text": {}, "parent_boundary": {}}},
                },
            },
        )
    )

    assert [event.text for event in events if isinstance(event, StreamDelta)] == ["ordinary reply"]
    decisions = [event.payload for event in events if isinstance(event, StreamParentBoundaryDecision)]
    assert decisions == [{
        "schema_version": "parent-boundary-v1",
        "category": "RELIGION",
        "applies": True,
        "model_action": "REDIRECT_TO_PARENT",
        "redirect": None,
    }]
    assert events[-1].result.output["parent_boundary"] == decisions[0]


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
