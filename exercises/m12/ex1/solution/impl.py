"""Ex 12.1: critique a 90-day adoption plan against the course ladder."""

from __future__ import annotations

from typing import Any

import ladder


def critique(plan: dict[str, Any], team: ladder.Team) -> list[str]:
    findings: list[str] = []
    level = team.level
    have = set(team.capabilities) | set(team.artifacts)
    for n, stage in enumerate(plan["stages"], 1):
        target = stage["target"]
        have |= set(stage.get("adds", []))
        if target > level + 1:
            findings.append(f"stage {n}: skips from L{level} to L{target}")
        if target >= ladder.NOT_A_TARGET:
            findings.append(f"stage {n}: targets L{target}")
        for lvl in range(level + 1, min(target, ladder.NOT_A_TARGET - 1) + 1):
            need = ladder.ENTRY[lvl]
            findings += [
                f"stage {n}: missing {item}"
                for item in (*need["capabilities"], *need["artifacts"])
                if item not in have
            ]
        if target >= 3:
            prs, hours = stage["agent_prs_per_week"], stage["reviewer_hours_per_week"]
            load = float("inf") if hours == 0 else round(prs * team.review_hours_per_pr / hours, 2)
            if load > ladder.MAX_REVIEW_LOAD:
                findings.append(f"stage {n}: review load {load}")
        level = max(level, target)
    return findings
