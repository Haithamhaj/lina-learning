"""Explicit transient OpenAI adapter for Student-source safety signals."""

from __future__ import annotations

import base64
from collections.abc import Callable, Iterable
from dataclasses import dataclass
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


_SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@dataclass(frozen=True, slots=True)
class ModerationImage:
    content_type: str
    content: bytes


@dataclass(frozen=True, slots=True)
class SourceModerationSignal:
    """Only bounded provider signals; scores and raw responses are discarded."""

    model: str
    flagged: bool
    true_categories: frozenset[str]
    applied_input_types: dict[str, tuple[str, ...]]


class SourceModerationProviderError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"OpenAI source moderation failed ({code}).")


class OpenAIMultimodalModerationProvider:
    """Classify transient text/image inputs with the official moderation API."""

    model = "omni-moderation-latest"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
        request_sender: Callable[..., Any] = urlopen,
    ) -> None:
        self._api_key = api_key
        self._url = f"{(base_url or 'https://api.openai.com').rstrip('/')}/v1/moderations"
        self._timeout_seconds = timeout_seconds
        self._request_sender = request_sender

    def inspect(
        self,
        *,
        text: str,
        images: Iterable[ModerationImage],
    ) -> SourceModerationSignal:
        image_items = tuple(images)
        normalized_text = text.strip()
        if not normalized_text and not image_items:
            raise ValueError("Source moderation input is empty.")
        moderation_input: list[dict[str, object]] = []
        if normalized_text:
            moderation_input.append({"type": "text", "text": normalized_text})
        for image in image_items:
            if image.content_type not in _SUPPORTED_IMAGE_TYPES:
                raise ValueError("Source moderation image type is unsupported.")
            if not image.content:
                raise ValueError("Source moderation image input is empty.")
            encoded = base64.b64encode(image.content).decode("ascii")
            moderation_input.append({
                "type": "image_url",
                "image_url": {"url": f"data:{image.content_type};base64,{encoded}"},
            })
        request = Request(
            self._url,
            data=json.dumps({"model": self.model, "input": moderation_input}).encode(),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self._request_sender(request, timeout=self._timeout_seconds) as response:
                raw = response.read()
        except HTTPError:
            raise SourceModerationProviderError("provider_error") from None
        except TimeoutError:
            raise SourceModerationProviderError("timeout") from None
        except URLError as error:
            code = "timeout" if isinstance(error.reason, TimeoutError) else "network_error"
            raise SourceModerationProviderError(code) from None
        try:
            result = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
            raise SourceModerationProviderError("invalid_response") from None
        return _bounded_signal(result, expected_model=self.model)


def _bounded_signal(result: object, *, expected_model: str) -> SourceModerationSignal:
    if not isinstance(result, dict) or not isinstance(result.get("results"), list) or not result["results"]:
        raise SourceModerationProviderError("invalid_response")
    true_categories: set[str] = set()
    applied: dict[str, list[str]] = {}
    flagged = False
    for item in result["results"]:
        if not isinstance(item, dict):
            raise SourceModerationProviderError("invalid_response")
        categories = item.get("categories")
        input_types = item.get("category_applied_input_types")
        if not isinstance(categories, dict) or not isinstance(input_types, dict):
            raise SourceModerationProviderError("invalid_response")
        flagged = flagged or item.get("flagged") is True
        true_categories.update(
            key for key, value in categories.items() if isinstance(key, str) and value is True
        )
        for category, values in input_types.items():
            if not isinstance(category, str) or not isinstance(values, list):
                continue
            admitted = applied.setdefault(category, [])
            for value in values:
                if value in {"text", "image"} and value not in admitted:
                    admitted.append(value)
    model = result.get("model")
    return SourceModerationSignal(
        model=model if isinstance(model, str) and model else expected_model,
        flagged=flagged,
        true_categories=frozenset(true_categories),
        applied_input_types={key: tuple(values) for key, values in sorted(applied.items())},
    )
