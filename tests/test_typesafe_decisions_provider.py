from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from services.model_gateway.factory import create_jev_decision_gateway
from services.model_gateway.gateway import ModelRoute
from services.model_gateway.typesafe_decisions_provider import (
    TypeSafeDecisionProviderError,
    TypeSafeDecisionsProvider,
)
from services.platform.config import Settings
from services.platform.db.models import ModelTask


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


def test_typesafe_adapter_uses_native_system_one_contract_and_normalizes_cost() -> None:
    captured: dict[str, object] = {}

    def send(request: object, *, timeout: float) -> _Response:
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response(
            {
                "model": "jev-1.13.0",
                "answers": {
                    "use_visual": {"type": "noul", "noul": 0.94},
                    "category": {
                        "type": "choice",
                        "choice": "PROCESS",
                        "probabilities": {"PROCESS": 0.91, "NONE": 0.09},
                        "confidence": 0.82,
                    },
                },
                "usage": {"input_tokens": 120, "output_tokens": 7},
            }
        )

    result = TypeSafeDecisionsProvider(
        api_key="test-only",
        timeout_seconds=4.5,
        request_sender=send,
    ).execute(
        ModelRoute("typesafe-decisions", "jev-1.13.0"),
        {
            "state": {"student": "How does sunlight reach us?"},
            "questions": {
                "use_visual": {
                    "type": "noul",
                    "instructions": "Would a visual materially help?",
                    "true_when": "The concept is primarily spatial or process-based.",
                    "false_when": "A concise verbal explanation is sufficient.",
                },
                "category": {
                    "type": "choice",
                    "instructions": "Choose the visual category.",
                    "criteria": {"PROCESS": "A sequence or flow.", "NONE": "No visual need."},
                },
            },
        },
    )

    request = captured["request"]
    body = json.loads(request.data.decode())
    assert request.full_url == "https://api.typesafe.ai/v1/systemone"
    assert body["model"] == "jev-1.13.0"
    assert body["state"] == {"student": "How does sunlight reach us?"}
    assert body["questions"]["use_visual"] == {
        "type": "noul",
        "instructions": "Would a visual materially help?",
        "criteria": {
            "true": "The concept is primarily spatial or process-based.",
            "false": "A concise verbal explanation is sufficient.",
        },
    }
    assert request.headers["Authorization"] == "Bearer test-only"
    assert captured["timeout"] == 4.5
    assert result.output["resolved_model"] == "jev-1.13.0"
    assert result.output["resolved_provider"] == "TypeSafe"
    assert result.input_tokens == 120
    assert result.output_tokens == 7
    assert result.estimated_cost_usd == pytest.approx(0.00000504)


def test_typesafe_adapter_fails_with_bounded_provider_error() -> None:
    def send(request: object, *, timeout: float):
        del request, timeout
        raise HTTPError("https://api.typesafe.ai/v1/systemone", 529, "overloaded", {}, None)

    provider = TypeSafeDecisionsProvider(api_key="test-only", request_sender=send)
    with pytest.raises(TypeSafeDecisionProviderError, match="http_529"):
        provider.execute(
            ModelRoute("typesafe-decisions", "jev-1.13.0"),
            {
                "state": "bounded state",
                "questions": {
                    "route": {
                        "type": "choice",
                        "instructions": "Pick one.",
                        "criteria": {"A": "a", "B": "b"},
                    }
                },
            },
        )


def test_typesafe_provider_selection_is_explicit_and_has_no_hidden_openrouter_fallback() -> None:
    provider = object()
    settings = Settings(
        _env_file=None,
        jev_provider="typesafe",
        typesafe_api_key="test-only",
        jev_visual_need_mode="shadow",
    )

    gateway = create_jev_decision_gateway(
        object(),
        task=ModelTask.VISUAL_NEED_DECISION,
        settings=settings,
        provider=provider,
    )

    route = gateway.route_for(ModelTask.VISUAL_NEED_DECISION)
    assert route.provider == "typesafe-decisions"
    assert route.model == "jev-1.13.0"


def test_enabled_typesafe_route_requires_typesafe_key_not_openrouter_key() -> None:
    with pytest.raises(ValueError, match="TYPESAFE_API_KEY"):
        Settings(
            _env_file=None,
            jev_provider="typesafe",
            jev_visual_need_mode="active",
            openrouter_api_key="wrong-transport-only",
        )
