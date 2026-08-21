"""OpenAI embedding adapter contained inside the Model Gateway boundary."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.request import Request, urlopen

from .gateway import ModelResult, ModelRoute


class OpenAIEmbeddingProvider:
    def __init__(self, *, api_key: str, base_url: str | None = None, timeout_seconds: float = 30.0, request_sender: Callable[[Request, float], Any] = urlopen) -> None:
        self._api_key = api_key
        self._url = f"{(base_url or 'https://api.openai.com').rstrip('/')}/v1/embeddings"
        self._timeout_seconds = timeout_seconds
        self._request_sender = request_sender

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        inputs = payload.get("input")
        if not isinstance(inputs, list) or not all(isinstance(value, str) for value in inputs):
            raise ValueError("Embedding input must be a list of strings.")
        body: dict[str, object] = {"model": route.model, "input": inputs}
        if "dimensions" in payload:
            body["dimensions"] = int(payload["dimensions"])
        request = Request(self._url, data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}, method="POST")
        with self._request_sender(request, timeout=self._timeout_seconds) as response:
            result = json.loads(response.read())
        data = result.get("data") if isinstance(result, dict) else None
        if not isinstance(data, list):
            raise ValueError("OpenAI Embeddings API returned invalid data.")
        embeddings = [row.get("embedding") for row in data if isinstance(row, dict)]
        if len(embeddings) != len(inputs) or not all(isinstance(vector, list) and all(isinstance(value, (int, float)) for value in vector) for vector in embeddings):
            raise ValueError("OpenAI Embeddings API returned invalid vectors.")
        usage = result.get("usage") if isinstance(result, dict) else None
        tokens = int(usage["prompt_tokens"]) if isinstance(usage, dict) and usage.get("prompt_tokens") is not None else None
        return ModelResult(output={"embeddings": embeddings}, input_tokens=tokens)
