"""OpenRouter Decisions adapter for bounded typed decisions.

The adapter is deliberately domain-agnostic: domains own the state, questions,
allowed answers and confidence policy.  It only transports the typed request
and normalizes usage for the existing Model Gateway ledger.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.model_gateway.gateway import ModelResult, ModelRoute


OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


class OpenRouterDecisionProviderError(RuntimeError):
    """A bounded decision request failed or returned an invalid contract."""


class OpenRouterDecisionsProvider:
    """Execute Jev-compatible typed decisions without leaking provider details."""

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 5.0,
        base_url: str = OPENROUTER_DECISIONS_URL,
        request_sender: Callable[..., object] | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenRouter API key is required.")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._base_url = base_url.rstrip("/")
        self._request_sender = request_sender or urlopen

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        state = payload.get("state")
        questions = payload.get("questions")
        if not isinstance(state, dict) or not isinstance(questions, dict) or not questions:
            raise ValueError("Decision payload requires non-empty state and questions objects.")

        body = json.dumps(
            {"model": route.model, "state": state, "questions": questions},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        request = Request(
            self._base_url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with self._request_sender(request, timeout=self._timeout_seconds) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise OpenRouterDecisionProviderError(type(error).__name__) from None

        if not isinstance(decoded, dict) or not isinstance(decoded.get("answers"), dict):
            raise OpenRouterDecisionProviderError("invalid_response")
        usage = decoded.get("usage") if isinstance(decoded.get("usage"), dict) else {}
        input_tokens = _optional_nonnegative_int(usage.get("input_tokens"))
        output_tokens = _optional_nonnegative_int(usage.get("output_tokens"))
        cost = _optional_nonnegative_float(usage.get("cost"))
        return ModelResult(
            output={
                "answers": decoded["answers"],
                "resolved_model": decoded.get("model"),
                "resolved_provider": decoded.get("provider"),
            },
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
        )


def _optional_nonnegative_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _optional_nonnegative_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    return None
