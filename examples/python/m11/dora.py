"""M11 L11.6: DORA's five software delivery metrics, before and after adopting agents.

Definitions from dora.dev/guides/dora-metrics (last updated 5 Jan 2026):
throughput = change lead time, deployment frequency, failed deployment recovery time;
instability = change fail rate, deployment rework rate.
Review latency (PR opened → first review) is an extra, team-level signal.

`fictional_team` makes up data for a made-up team. Nothing here is a benchmark. The
comparison rules (minimum sample size, the amplifier warning) are this course's.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median


@dataclass
class Deployment:
    at: datetime
    commit_times: list[datetime]
    failed: bool = False
    recovered_at: datetime | None = None
    unplanned: bool = False  # deployed because of a production incident


@dataclass
class PullRequest:
    opened: datetime
    first_review: datetime


def hours(td: timedelta) -> float:
    return td.total_seconds() / 3600


def metrics(deps: list[Deployment], prs: list[PullRequest], weeks: float) -> dict[str, float]:
    recoveries = [
        hours(d.recovered_at - d.at) for d in deps if d.failed and d.recovered_at is not None
    ]
    return {
        "deployment_frequency_per_week": round(len(deps) / weeks, 2),
        "change_lead_time_h": round(
            median(hours(d.at - c) for d in deps for c in d.commit_times), 1
        ),
        "failed_deployment_recovery_time_h": round(median(recoveries), 1) if recoveries else 0.0,
        "change_fail_rate": round(sum(d.failed for d in deps) / len(deps), 3),
        "deployment_rework_rate": round(sum(d.unplanned for d in deps) / len(deps), 3),
        "review_latency_h": round(median(hours(p.first_review - p.opened) for p in prs), 1),
    }


def compare(
    before: dict[str, float], after: dict[str, float], n_before: int, n_after: int, min_n: int = 20
) -> list[str]:
    notes = []
    if min(n_before, n_after) < min_n:
        notes.append(f"too few deployments to compare (need {min_n} per window)")
    faster = after["deployment_frequency_per_week"] > before["deployment_frequency_per_week"]
    less_stable = (
        after["change_fail_rate"] > before["change_fail_rate"]
        or after["deployment_rework_rate"] > before["deployment_rework_rate"]
    )
    if faster and less_stable:
        notes.append("amplifier warning: throughput up, instability up")
    if after["review_latency_h"] > 1.5 * before["review_latency_h"]:
        notes.append("review is the new bottleneck: latency up more than 50%")
    return notes


def fictional_team(
    seed: int, weeks: int, per_week: int, fail_p: float, rework_p: float, review_h: float
) -> tuple[list[Deployment], list[PullRequest]]:
    rng = random.Random(seed)
    start = datetime(2026, 1, 5, 9)
    deps, prs = [], []
    for i in range(weeks * per_week):
        at = start + timedelta(hours=i * 168 / per_week)
        commits = [at - timedelta(hours=rng.uniform(4, 60)) for _ in range(rng.randint(1, 4))]
        failed = rng.random() < fail_p
        deps.append(
            Deployment(
                at,
                commits,
                failed,
                at + timedelta(hours=rng.uniform(0.5, 6)) if failed else None,
                rng.random() < rework_p,
            )
        )
        opened = commits[0]
        prs.append(PullRequest(opened, opened + timedelta(hours=rng.uniform(0.5, 2 * review_h))))
    return deps, prs
