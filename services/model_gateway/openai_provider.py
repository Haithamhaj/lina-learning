"""OpenAI adapter for the Model Gateway."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen

from services.model_gateway.gateway import (
    ModelResult,
    ModelRoute,
    ModelStreamEvent,
    StreamComplete,
    StreamDelta,
)


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
        body = _request_body(route, payload)
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

        return _model_result(route, result, _normalize_output(_response_text(result), payload))

    def stream(self, route: ModelRoute, payload: dict[str, object]) -> Iterator[ModelStreamEvent]:
        """Forward actual Responses API deltas from one provider request."""

        body = _request_body(route, payload)
        body["stream"] = True
        request = Request(
            self._responses_url,
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        parts: list[str] = []
        text_extractor = _StructuredTutorTextExtractor() if _has_response_schema(payload) else None
        with self._request_sender(request, timeout=self._timeout_seconds) as response:
            for raw_line in response:
                line = raw_line.decode().strip() if isinstance(raw_line, bytes) else str(raw_line).strip()
                if not line.startswith("data: "):
                    continue
                event = json.loads(line.removeprefix("data: "))
                if not isinstance(event, dict):
                    continue
                event_type = event.get("type")
                if event_type == "response.output_text.delta":
                    delta = event.get("delta")
                    if isinstance(delta, str) and delta:
                        parts.append(delta)
                        student_text = text_extractor.feed(delta) if text_extractor is not None else delta
                        if student_text:
                            yield StreamDelta(student_text)
                    continue
                if event_type == "response.completed":
                    response_data = event.get("response")
                    if not isinstance(response_data, dict):
                        raise ValueError("OpenAI Responses API completed without a response.")
                    raw_text = "".join(parts).strip() or _response_text(response_data)
                    output = _normalize_output(
                        raw_text,
                        payload,
                        fallback_text=text_extractor.text if text_extractor is not None else None,
                    )
                    yield StreamComplete(_model_result(route, response_data, output))
                    return
                if event_type == "response.failed":
                    raise ValueError("OpenAI Responses API streaming request failed.")
                if event_type == "response.incomplete":
                    response_data = event.get("response")
                    incomplete_details = response_data.get("incomplete_details") if isinstance(response_data, dict) else None
                    reason = incomplete_details.get("reason") if isinstance(incomplete_details, dict) else None
                    detail = f": {reason}" if isinstance(reason, str) and reason else ""
                    raise ValueError(f"OpenAI Responses API incomplete{detail}.")
        raise ValueError("OpenAI Responses API stream ended without a completion event.")


def _request_body(route: ModelRoute, payload: dict[str, object]) -> dict[str, object]:
    body: dict[str, object] = {
        "model": route.model,
        "instructions": str(payload["instructions"]),
        "input": str(payload["input"]),
        "store": False,
    }
    if "max_output_tokens" in payload:
        body["max_output_tokens"] = int(payload["max_output_tokens"])
    response_schema = payload.get("response_schema")
    if isinstance(response_schema, dict):
        name = response_schema.get("name")
        schema = response_schema.get("schema")
        if isinstance(name, str) and isinstance(schema, dict):
            body["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": name,
                    "schema": schema,
                    "strict": True,
                }
            }
    return body


def _model_result(route: ModelRoute, result: object, output: dict[str, object]) -> ModelResult:
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
        output=output,
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


def _has_response_schema(payload: dict[str, object]) -> bool:
    response_schema = payload.get("response_schema")
    return isinstance(response_schema, dict) and isinstance(response_schema.get("name"), str)


def _normalize_output(
    text: str,
    payload: dict[str, object],
    *,
    fallback_text: str | None = None,
) -> dict[str, object]:
    if not _has_response_schema(payload):
        return {"text": text}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        if fallback_text:
            return {
                "text": fallback_text,
                "suggested_actions": [],
                "candidate_metadata": None,
                "candidate_metadata_error": "structured_output_invalid_json",
            }
        raise ValueError("OpenAI structured Tutor output is not valid JSON.") from None
    if not isinstance(parsed, dict) or not isinstance(parsed.get("text"), str) or not parsed["text"].strip():
        raise ValueError("OpenAI structured Tutor output has no student-facing text.")
    if "candidate_metadata" not in parsed:
        return {
            "text": parsed["text"],
            "suggested_actions": parsed.get("suggested_actions", []),
            "candidate_metadata": None,
            "candidate_metadata_error": "candidate_metadata_missing",
            **_teaching_decision_output(parsed),
        }
    return {
        "text": parsed["text"],
        "suggested_actions": parsed.get("suggested_actions", []),
        "candidate_metadata": parsed["candidate_metadata"],
        **_teaching_decision_output(parsed),
    }


def _teaching_decision_output(parsed: dict[str, object]) -> dict[str, object]:
    """Preserve supplied v5 semantic decisions without fabricating absent values."""

    fields = ("teaching_mode", "teaching_strategy", "teaching_method_id", "prior_method_relation")
    return {field: parsed[field] for field in fields if field in parsed}


class _StructuredTutorTextExtractor:
    """Emit only the `text` JSON-string value while retaining raw structured output."""

    _TEXT_PREFIX = re.compile(r'"text"\s*:\s*"')

    def __init__(self) -> None:
        self._prefix = ""
        self._started = False
        self._complete = False
        self._escaped = False
        self._unicode_digits = ""
        self.text = ""

    def feed(self, delta: str) -> str:
        if self._complete:
            return ""
        if not self._started:
            self._prefix += delta
            match = self._TEXT_PREFIX.search(self._prefix)
            if match is None:
                return ""
            self._started = True
            delta = self._prefix[match.end():]
            self._prefix = ""
        emitted: list[str] = []
        for character in delta:
            if self._unicode_digits:
                self._unicode_digits += character
                if len(self._unicode_digits) == 4:
                    emitted.append(chr(int(self._unicode_digits, 16)))
                    self._unicode_digits = ""
                    self._escaped = False
                continue
            if self._escaped:
                if character == "u":
                    self._unicode_digits = ""
                    continue
                emitted.append({"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f"}.get(character, character))
                self._escaped = False
                continue
            if character == "\\":
                self._escaped = True
                continue
            if character == '"':
                self._complete = True
                break
            emitted.append(character)
        chunk = "".join(emitted)
        self.text += chunk
        return chunk


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
