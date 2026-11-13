"""Ex 12.1: critique a 90-day adoption plan against the course ladder."""

from __future__ import annotations

from typing import Any

import ladder


def critique(plan: dict[str, Any], team: ladder.Team) -> list[str]:
    findings: list[str] = []
    level = team.level
    for n, stage in enumerate(plan["stages"], 1):
        if stage["target"] > level + 1:
            findings.append(f"stage {n}: skips from L{level} to L{stage['target']}")
        level = stage["target"]
    # TODO: L5, missing prerequisites, review load
    return findings
