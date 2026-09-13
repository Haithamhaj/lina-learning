"""Shared configured token rate card; estimates exclude hosted-tool charges."""
from dataclasses import dataclass

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


def estimate_openai_cost(
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
