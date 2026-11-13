"""L8.4: production plumbing for agents: idempotency keys, rate limits, tenant isolation,
and secrets that never reach prompts or logs. Plain Python, no framework.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class IdempotencyConflict(Exception):
    """Same key, different request: a client bug, never silently 'succeed'."""


@dataclass
class IdempotencyStore:
    """Stores (request fingerprint, response) per key, like Stripe-style idempotency keys."""

    seen: dict[str, tuple[str, Any]] = field(default_factory=dict)

    def run(self, key: str, request: dict[str, Any], fn: Callable[[], Any]) -> tuple[Any, bool]:
        fp = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        if key in self.seen:
            old_fp, response = self.seen[key]
            if old_fp != fp:
                raise IdempotencyConflict(key)
            return response, False
        response = fn()
        self.seen[key] = (fp, response)
        return response, True


@dataclass
class TokenBucket:
    """`rate` tokens per second, bursts up to `capacity`. Time is injected for tests."""

    rate: float
    capacity: float
    tokens: float = -1.0
    last: float = 0.0

    def allow(self, now: float, cost: float = 1.0) -> bool:
        if self.tokens < 0:
            self.tokens, self.last = self.capacity, now
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


@dataclass
class Tenants:
    """Per-tenant queues, budgets and buckets: one noisy tenant can't starve the others."""

    daily_usd: dict[str, float]
    rate_per_s: float = 2.0
    spent: dict[str, float] = field(default_factory=dict)
    buckets: dict[str, TokenBucket] = field(default_factory=dict)

    def queue(self, tenant: str) -> str:
        return f"agents-{tenant}"  # e.g. a Temporal task queue per tenant (or per tier)

    def admit(self, tenant: str, est_usd: float, now: float) -> str:
        if tenant not in self.daily_usd:
            return "rejected: unknown tenant"
        if self.spent.get(tenant, 0.0) + est_usd > self.daily_usd[tenant]:
            return "rejected: daily budget"
        bucket = self.buckets.setdefault(tenant, TokenBucket(self.rate_per_s, self.rate_per_s * 2))
        if not bucket.allow(now):
            return "throttled"
        self.spent[tenant] = self.spent.get(tenant, 0.0) + est_usd
        return "admitted"


SECRET = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})")


def redact(text: str) -> str:
    return SECRET.sub("[REDACTED]", text)


def secret(name: str) -> str:
    """Read a secret at the edge (tool code), never pass it through the model's context."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing secret {name}")
    return value
