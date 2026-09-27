"""Shared direct-OpenAI token rate card; estimates exclude hosted-tool charges."""

from __future__ import annotations

from dataclasses import dataclass


LONG_CONTEXT_THRESHOLD_TOKENS = 272_000


@dataclass(frozen=True)
class _TokenPricing:
    input_per_million: float
    cached_input_per_million: float
    cache_write_per_million: float
    output_per_million: float


# Direct OpenAI API Standard processing, verified 2026-09-28.
_STANDARD_SHORT_CONTEXT_PRICING = {
    "gpt-5.6-luna": _TokenPricing(
        input_per_million=0.20,
        cached_input_per_million=0.02,
        cache_write_per_million=0.25,
        output_per_million=1.20,
    ),
    "gpt-6-luna": _TokenPricing(
        input_per_million=0.10,
        cached_input_per_million=0.01,
        cache_write_per_million=0.125,
        output_per_million=0.50,
    ),
    "gpt-6-sol": _TokenPricing(
        input_per_million=2.00,
        cached_input_per_million=0.20,
        cache_write_per_million=2.50,
        output_per_million=10.00,
    ),
}


def estimate_openai_cost(
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    *,
    cached_input_tokens: int,
    cache_write_tokens: int,
) -> float | None:
    """Estimate configured Standard-processing routes from Responses usage."""

    pricing = _STANDARD_SHORT_CONTEXT_PRICING.get(model)
    if pricing is None or input_tokens is None or output_tokens is None:
        return None
    if input_tokens < 0 or output_tokens < 0:
        return None
    cached_input_tokens = min(max(cached_input_tokens, 0), input_tokens)
    cache_write_tokens = min(
        max(cache_write_tokens, 0), input_tokens - cached_input_tokens
    )
    normal_input_tokens = input_tokens - cached_input_tokens - cache_write_tokens

    # OpenAI applies long-context multipliers to the full request once prompt
    # input exceeds 272K tokens: 2x input/cache rates and 1.5x output.
    input_multiplier = 2.0 if input_tokens > LONG_CONTEXT_THRESHOLD_TOKENS else 1.0
    output_multiplier = 1.5 if input_tokens > LONG_CONTEXT_THRESHOLD_TOKENS else 1.0
    return round(
        (
            normal_input_tokens * pricing.input_per_million * input_multiplier
            + cached_input_tokens
            * pricing.cached_input_per_million
            * input_multiplier
            + cache_write_tokens
            * pricing.cache_write_per_million
            * input_multiplier
            + output_tokens * pricing.output_per_million * output_multiplier
        )
        / 1_000_000,
        10,
    )
