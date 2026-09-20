from __future__ import annotations

import json

import pytest

from services.model_gateway.factory import create_jev_decision_gateway
from services.model_gateway.gateway import ModelRoute
from services.model_gateway.openrouter_decisions_provider import OpenRouterDecisionsProvider
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


def test_decisions_adapter_sends_only_typed_state_and_questions() -> None:
    captured: dict[str, object] = {}

    def send(request: object, *, timeout: float) -> _Response:
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response(
            {
                "model": "typesafe/jev-1.13-20260917",
                "provider": "TypeSafe",
                "answers": {"route": {"choice": "reuse", "probabilities": {"reuse": 0.96, "none": 0.04}}},
                "usage": {"input_tokens": 120, "output_tokens": 0, "cost": 0.00000504},
            }
        )

    result = OpenRouterDecisionsProvider(
        api_key="test-only",
        timeout_seconds=4.5,
        request_sender=send,
    ).execute(
        ModelRoute("openrouter-decisions", "typesafe/jev-1.13"),
        {
            "state": {"brief": "show thirds"},
            "questions": {
                "route": {
                    "type": "choice",
                    "instructions": "Choose one authorized action.",
                    "criteria": {"reuse": "exact fit", "none": "no exact fit"},
                }
            },
        },
    )

    request = captured["request"]
    body = json.loads(request.data.decode())
    assert request.full_url == "https://openrouter.ai/api/alpha/decisions"
    assert body == {
        "model": "typesafe/jev-1.13",
        "state": {"brief": "show thirds"},
        "questions": {
            "route": {
                "type": "choice",
                "instructions": "Choose one authorized action.",
                "criteria": {"reuse": "exact fit", "none": "no exact fit"},
            }
        },
    }
    assert request.headers["Authorization"] == "Bearer test-only"
    assert captured["timeout"] == 4.5
    assert result.output["answers"] == {
        "route": {"choice": "reuse", "probabilities": {"reuse": 0.96, "none": 0.04}}
    }
    assert result.input_tokens == 120
    assert result.output_tokens == 0
    assert result.estimated_cost_usd == pytest.approx(0.00000504)


def test_jev_modes_are_off_by_default_and_require_key_when_enabled() -> None:
    settings = Settings(_env_file=None)
    assert settings.jev_visual_personalization_mode == "off"
    assert settings.jev_canvas_reuse_mode == "off"
    assert settings.jev_segment_rubric_mode == "off"
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        Settings(_env_file=None, jev_canvas_reuse_mode="active")


def test_jev_thresholds_and_policy_identities_are_experimental_configuration() -> None:
    settings = Settings(
        _env_file=None,
        openrouter_api_key="test-only",
        jev_visual_personalization_mode="shadow",
        jev_visual_personalization_policy_version="visual-calibration-v2",
        jev_visual_personalization_min_probability=0.61,
        jev_canvas_reuse_mode="shadow",
        jev_canvas_reuse_policy_version="reuse-calibration-v3",
        jev_canvas_reuse_min_probability=0.83,
        jev_canvas_reuse_min_margin=0.17,
    )

    assert settings.jev_visual_personalization_policy_version == "visual-calibration-v2"
    assert settings.jev_visual_personalization_min_probability == pytest.approx(0.61)
    assert settings.jev_canvas_reuse_policy_version == "reuse-calibration-v3"
    assert settings.jev_canvas_reuse_min_probability == pytest.approx(0.83)
    assert settings.jev_canvas_reuse_min_margin == pytest.approx(0.17)


def test_decision_gateway_rejects_non_jev_tasks() -> None:
    with pytest.raises(ValueError, match="not a Jev"):
        create_jev_decision_gateway(
            object(),
            task=ModelTask.TUTOR,
            settings=Settings(_env_file=None),
            provider=object(),
        )
