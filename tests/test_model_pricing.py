from __future__ import annotations

import pytest

from services.model_gateway.pricing import estimate_openai_cost


@pytest.mark.parametrize(
    "model,rates",
    [
        ("gpt-5.6-luna", (0.20, 0.02, 0.25, 1.20)),
        ("gpt-6-luna", (0.10, 0.01, 0.125, 0.50)),
        ("gpt-6-sol", (2.00, 0.20, 2.50, 10.00)),
    ],
)
def test_standard_short_context_rate_cards(model: str, rates: tuple[float, ...]) -> None:
    normal, cached, write, output = rates
    cost = estimate_openai_cost(
        model,
        3_000_000,
        1_000_000,
        cached_input_tokens=1_000_000,
        cache_write_tokens=1_000_000,
    )
    # 3M input intentionally crosses the long-context boundary.
    expected = (normal * 2 + cached * 2 + write * 2) + output * 1.5
    assert cost == pytest.approx(expected)


def test_gpt6_luna_short_context_cost_uses_current_rates() -> None:
    cost = estimate_openai_cost(
        "gpt-6-luna",
        100_000,
        10_000,
        cached_input_tokens=20_000,
        cache_write_tokens=10_000,
    )
    expected = (
        70_000 * 0.10
        + 20_000 * 0.01
        + 10_000 * 0.125
        + 10_000 * 0.50
    ) / 1_000_000
    assert cost == pytest.approx(expected)


def test_long_context_threshold_applies_full_request_multipliers() -> None:
    cost = estimate_openai_cost(
        "gpt-6-sol",
        272_001,
        20_000,
        cached_input_tokens=20_000,
        cache_write_tokens=2_000,
    )
    normal = 250_001
    expected = (
        normal * 2.00 * 2
        + 20_000 * 0.20 * 2
        + 2_000 * 2.50 * 2
        + 20_000 * 10.00 * 1.5
    ) / 1_000_000
    assert cost == pytest.approx(expected)


def test_unknown_model_has_no_fabricated_estimate() -> None:
    assert (
        estimate_openai_cost(
            "unknown",
            100,
            10,
            cached_input_tokens=0,
            cache_write_tokens=0,
        )
        is None
    )
