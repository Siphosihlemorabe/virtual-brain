"""What each model costs, to record the dollar cost of every call. Anthropic list prices, USD per million tokens.

Update when prices change; an unknown model is recorded with cost 0 and a clear flag in the call log.
"""

PRICES_PER_MILLION: dict[str, tuple[float, float]] = {  # model: (input, output)
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5": (5.00, 25.00),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """The call's cost in US dollars, or None if the model's price is unknown."""
    prices = PRICES_PER_MILLION.get(model)
    if prices is None:
        return None
    return (input_tokens * prices[0] + output_tokens * prices[1]) / 1_000_000
