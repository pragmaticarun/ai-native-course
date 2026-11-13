"""L6.6: cost and latency engineering.

* routing: send easy requests to a small model, hard ones to a large one;
* caching: identical (model, prompt) pairs are answered from a cache;
* parallel tool calls: independent tools run concurrently (asyncio.gather);
* budgets: a per-run token/cost budget that stops the run gracefully;
* circuit breaker: after N consecutive provider failures, stop calling for a cooldown.

Prices are ILLUSTRATIVE (not any provider's list price).
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

PRICES = {"small": (0.10, 0.40), "large": (2.00, 8.00)}  # illustrative USD per 1M (input, output)


def route(prompt: str) -> str:
    """Toy router. Real routers use a classifier or the small model's own confidence."""
    hard = any(w in prompt.lower() for w in ("prove", "refactor", "design", "multi-step", "why"))
    return "large" if hard or len(prompt) > 2_000 else "small"


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = PRICES[model]
    return (input_tokens * pin + output_tokens * pout) / 1e6


@dataclass
class Cache:
    capacity: int = 256
    hits: int = 0
    misses: int = 0
    _data: OrderedDict = field(default_factory=OrderedDict)

    def get_or_call(self, model: str, prompt: str, call: Callable[[], str]) -> str:
        key = (model, prompt)
        if key in self._data:
            self.hits += 1
            self._data.move_to_end(key)
            return self._data[key]
        self.misses += 1
        value = call()
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)
        return value


async def run_tools(
    calls: list[Callable[[], Awaitable[str]]], parallel: bool
) -> tuple[list[str], float]:
    t0 = time.perf_counter()
    if parallel:
        results = list(await asyncio.gather(*(c() for c in calls)))
    else:
        results = [await c() for c in calls]
    return results, time.perf_counter() - t0


class BudgetExceeded(Exception):
    pass


@dataclass
class Budget:
    max_usd: float
    spent: float = 0.0

    def charge(self, model: str, input_tokens: int, output_tokens: int) -> None:
        c = cost(model, input_tokens, output_tokens)
        if self.spent + c > self.max_usd:
            raise BudgetExceeded(
                f"next call costs ${c:.4f}; spent ${self.spent:.4f} of ${self.max_usd:.4f}"
            )
        self.spent += c


def run_with_budget(steps: list[tuple[str, int, int]], budget: Budget) -> dict:
    """Each step is (model, input_tokens, output_tokens). Stops cleanly at the budget."""
    done = []
    try:
        for i, (model, tin, tout) in enumerate(steps):
            budget.charge(model, tin, tout)
            done.append(i)
    except BudgetExceeded as err:
        return {"status": "stopped_at_budget", "completed_steps": done, "reason": str(err)}
    return {"status": "completed", "completed_steps": done, "reason": ""}


@dataclass
class CircuitBreaker:
    threshold: int = 3
    cooldown_s: float = 30.0
    failures: int = 0
    opened_at: float | None = None
    clock: Callable[[], float] = time.monotonic

    def call(self, fn: Callable[[], str]) -> str:
        if self.opened_at is not None:
            if self.clock() - self.opened_at < self.cooldown_s:
                raise RuntimeError("circuit open: provider marked unhealthy, use fallback")
            self.opened_at = None  # half-open: try one call
        try:
            out = fn()
        except Exception:
            self.failures += 1
            if self.failures >= self.threshold:
                self.opened_at = self.clock()
            raise
        self.failures = 0
        return out
