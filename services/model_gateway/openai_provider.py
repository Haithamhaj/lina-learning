"""OpenAI adapter for the Model Gateway."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen

from services.model_gateway.gateway import ModelResult, ModelRoute


@dataclass(frozen=True)
class _TokenPricing:
    input_per_million: float
    cached_input_per_million: float
    cache_write_per_million: float
    output_per_million: float


# Direct OpenAI API, All models / standard short-context pricing. Keep this
# map deliberately small until another configured model needs an estimate.
_STANDARD_SHORT_CONTEXT_PRICING = {
    "gpt-5.6-luna": _TokenPricing(
        input_per_million=0.50,
        cached_input_per_million=0.05,
        cache_write_per_million=0.625,
        output_per_million=3.00,
    ),
}


class OpenAIResponsesProvider:
    """Execute text-generation requests through the OpenAI Responses API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
        request_sender: Callable[[Request, float], Any] = urlopen,
    ) -> None:
        self._api_key = api_key
        self._responses_url = f"{(base_url or 'https://api.openai.com').rstrip('/')}/v1/responses"
        self._timeout_seconds = timeout_seconds
        self._request_sender = request_sender

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        body: dict[str, object] = {
            "model": route.model,
            "instructions": str(payload["instructions"]),
            "input": str(payload["input"]),
            "store": False,
        }
        if "max_output_tokens" in payload:
            body["max_output_tokens"] = int(payload["max_output_tokens"])
        request = Request(
            self._responses_url,
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with self._request_sender(request, timeout=self._timeout_seconds) as response:
            result = json.loads(response.read())

        text = _response_text(result)
        usage = result.get("usage") if isinstance(result, dict) else None
        total_input_tokens = int(usage["input_tokens"]) if isinstance(usage, dict) and usage.get("input_tokens") is not None else None
        output_tokens = int(usage["output_tokens"]) if isinstance(usage, dict) and usage.get("output_tokens") is not None else None
        input_details = usage.get("input_tokens_details") if isinstance(usage, dict) else None
        cached_input_tokens = (
            int(input_details["cached_tokens"])
            if isinstance(input_details, dict) and input_details.get("cached_tokens") is not None
            else 0
        )
        cache_write_tokens = (
            int(input_details["cache_write_tokens"])
            if isinstance(input_details, dict) and input_details.get("cache_write_tokens") is not None
            else 0
        )
        if total_input_tokens is not None:
            cached_input_tokens = min(max(cached_input_tokens, 0), total_input_tokens)
            cache_write_tokens = min(
                max(cache_write_tokens, 0), total_input_tokens - cached_input_tokens
            )
        normal_input_tokens = (
            total_input_tokens - cached_input_tokens - cache_write_tokens
            if total_input_tokens is not None
            else None
        )
        return ModelResult(
            output={"text": text},
            input_tokens=normal_input_tokens,
            cached_input_tokens=cached_input_tokens,
            cache_write_tokens=cache_write_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=_estimate_cost(
                route.model,
                total_input_tokens,
                output_tokens,
                cached_input_tokens=cached_input_tokens,
                cache_write_tokens=cache_write_tokens,
            ),
        )


def _response_text(result: object) -> str:
    """Extract text without retaining provider response metadata in application state."""

    if not isinstance(result, dict):
        raise ValueError("OpenAI Responses API returned an invalid response.")
    parts: list[str] = []
    for output in result.get("output", []):
        if not isinstance(output, dict) or output.get("type") != "message":
            continue
        for content in output.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    text = "".join(parts).strip()
    if not text:
        raise ValueError("OpenAI Responses API returned no output text.")
    return text


def _estimate_cost(
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    *,
    cached_input_tokens: int,
    cache_write_tokens: int,
) -> float | None:
    """Estimate supported direct-OpenAI routes from Responses usage categories."""

    pricing = _STANDARD_SHORT_CONTEXT_PRICING.get(model)
    if pricing is None or input_tokens is None or output_tokens is None:
        return None
    cached_input_tokens = min(max(cached_input_tokens, 0), input_tokens)
    cache_write_tokens = min(
        max(cache_write_tokens, 0), input_tokens - cached_input_tokens
    )
    normal_input_tokens = input_tokens - cached_input_tokens - cache_write_tokens
    return round(
        (
            normal_input_tokens * pricing.input_per_million
            + cached_input_tokens * pricing.cached_input_per_million
            + cache_write_tokens * pricing.cache_write_per_million
            + output_tokens * pricing.output_per_million
        )
        / 1_000_000,
        10,
    )
