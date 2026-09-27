"""TypeSafe System One adapter for bounded Jev decisions.

Domain code owns the finite state/questions contract and all downstream policy.
This adapter only translates the existing provider-neutral decision payload to
TypeSafe's native wire shape and normalizes answers/usage for the shared ledger.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.model_gateway.gateway import ModelResult, ModelRoute


TYPESAFE_SYSTEM_ONE_URL = "https://api.typesafe.ai/v1/systemone"
TYPESAFE_INPUT_USD_PER_MILLION = 0.042


class TypeSafeDecisionProviderError(RuntimeError):
    """A TypeSafe bounded-decision request failed or violated its contract."""


class TypeSafeDecisionsProvider:
    """Execute Jev decisions through TypeSafe's direct System One endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 5.0,
        base_url: str = TYPESAFE_SYSTEM_ONE_URL,
        request_sender: Callable[..., object] | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("TypeSafe API key is required.")
        if timeout_seconds <= 0:
            raise ValueError("TypeSafe timeout must be positive.")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._base_url = base_url.rstrip("/")
        self._request_sender = request_sender or urlopen

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        state = payload.get("state")
        questions = payload.get("questions")
        if state is None or not isinstance(questions, dict) or not questions:
            raise ValueError("Decision payload requires state and non-empty questions.")

        body = json.dumps(
            {
                "model": route.model,
                "state": state,
                "questions": _native_questions(questions),
            },
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
        except HTTPError as error:
            raise TypeSafeDecisionProviderError(f"http_{error.code}") from None
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise TypeSafeDecisionProviderError(type(error).__name__) from None

        if not isinstance(decoded, dict) or not isinstance(decoded.get("answers"), dict):
            raise TypeSafeDecisionProviderError("invalid_response")
        usage = decoded.get("usage") if isinstance(decoded.get("usage"), dict) else {}
        input_tokens = _optional_nonnegative_int(usage.get("input_tokens"))
        output_tokens = _optional_nonnegative_int(usage.get("output_tokens"))
        cost = (
            round(input_tokens * TYPESAFE_INPUT_USD_PER_MILLION / 1_000_000, 10)
            if input_tokens is not None
            else None
        )
        return ModelResult(
            output={
                "answers": decoded["answers"],
                "resolved_model": decoded.get("model"),
                "resolved_provider": "TypeSafe",
            },
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
        )


def _native_questions(questions: dict[str, object]) -> dict[str, object]:
    """Translate provider-neutral Noul criteria without changing domain meaning."""

    normalized: dict[str, object] = {}
    for key, raw in questions.items():
        if not isinstance(key, str) or not isinstance(raw, dict):
            raise ValueError("Decision questions must be named objects.")
        question = dict(raw)
        question_type = question.get("type")
        if question_type not in {"choice", "score", "noul"}:
            raise ValueError("Decision question type is unsupported.")
        if question_type == "noul":
            true_when = question.pop("true_when", None)
            false_when = question.pop("false_when", None)
            if "criteria" not in question and (
                isinstance(true_when, str) or isinstance(false_when, str)
            ):
                criteria: dict[str, str] = {}
                if isinstance(true_when, str):
                    criteria["true"] = true_when
                if isinstance(false_when, str):
                    criteria["false"] = false_when
                question["criteria"] = criteria
        else:
            question.pop("true_when", None)
            question.pop("false_when", None)
        normalized[key] = question
    return normalized


def _optional_nonnegative_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None
