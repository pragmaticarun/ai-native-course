"""L2.5: token accounting and the effect of prompt caching.

Prices are PARAMETERS, not real vendor prices: plug in your provider's current
price sheet. The point is the shape of the calculation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Prices:
    input_per_mtok: float
    cached_input_per_mtok: float
    output_per_mtok: float


def run_cost(
    prefix_tokens: int,
    fresh_tokens: int,
    output_tokens: int,
    calls: int,
    prices: Prices,
    cache: bool,
) -> float:
    """Cost of `calls` requests sharing a stable prefix (system prompt + tools).

    With caching on, the first call pays full price for the prefix and later
    calls pay the cached rate (assumes every later call hits the cache).
    """
    total = 0.0
    for i in range(calls):
        prefix_rate = prices.cached_input_per_mtok if (cache and i > 0) else prices.input_per_mtok
        total += prefix_tokens * prefix_rate + fresh_tokens * prices.input_per_mtok
        total += output_tokens * prices.output_per_mtok
    return total / 1_000_000


if __name__ == "__main__":
    example = Prices(input_per_mtok=1.0, cached_input_per_mtok=0.1, output_per_mtok=4.0)
    args = dict(prefix_tokens=6000, fresh_tokens=300, output_tokens=200, calls=20, prices=example)
    print(f"no cache: {run_cost(**args, cache=False):.4f} units")  # type: ignore[arg-type]
    print(f"cache:    {run_cost(**args, cache=True):.4f} units")  # type: ignore[arg-type]
