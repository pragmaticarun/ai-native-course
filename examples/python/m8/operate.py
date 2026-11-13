"""L8.5: operating agents. SLOs and error budgets, burn-rate alerts, and pinned versions of
prompts/models/workflows so an incident can be replayed exactly.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Run:
    ok: bool
    latency_s: float
    cost_usd: float


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile (p in 0-100)."""
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]


def slo_report(
    runs: list[Run], target: float = 0.95, p95_budget_s: float = 30.0
) -> dict[str, float | bool]:
    success = sum(r.ok for r in runs) / len(runs)
    allowed_failures = (1 - target) * len(runs)
    failures = len(runs) - sum(r.ok for r in runs)
    return {
        "success_rate": round(success, 4),
        "p95_latency_s": percentile([r.latency_s for r in runs], 95),
        "error_budget_used": round(failures / allowed_failures, 2)
        if allowed_failures
        else float("inf"),
        "meets_slo": success >= target
        and percentile([r.latency_s for r in runs], 95) <= p95_budget_s,
    }


def burn_rate(failures: int, total: int, target: float) -> float:
    """How fast the error budget burns: 1.0 = exactly on budget for the window."""
    return (failures / total) / (1 - target)


def should_page(short_window: float, long_window: float, threshold: float = 14.4) -> bool:
    """Multi-window burn-rate alert (Google SRE workbook style): both windows must burn fast."""
    return short_window >= threshold and long_window >= threshold


@dataclass(frozen=True)
class Release:
    """Everything that changes agent behaviour, pinned together."""

    workflow_version: str
    model: str
    prompt: str
    tools: tuple[str, ...]

    @property
    def fingerprint(self) -> str:
        blob = "|".join([self.workflow_version, self.model, self.prompt, *self.tools])
        return hashlib.sha256(blob.encode()).hexdigest()[:12]


def diff(a: Release, b: Release) -> list[str]:
    return [
        f
        for f in ("workflow_version", "model", "prompt", "tools")
        if getattr(a, f) != getattr(b, f)
    ]
