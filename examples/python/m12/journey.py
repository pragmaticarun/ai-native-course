"""M12 worked example: a fictional six-person team ("Clipline", a video-tools product)
moving from L1 to L3 over one quarter. Every number here is invented for teaching.

The journey replays quarter snapshots through the ladder so the reader can see *why*
each move was or wasn't allowed, using the course's own entry criteria (ladder.py).

Run: cd examples/python && uv run --project ../../python python -m m12.journey
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

try:
    from m12.ladder import Team, ready_for
except ImportError:  # imported as a top-level module by the tests
    from ladder import Team, ready_for  # type: ignore[no-redef]

FIXTURES = Path(__file__).parent / "fixtures" / "team"


def snapshots() -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = yaml.safe_load((FIXTURES / "quarter.yaml").read_text())[
        "snapshots"
    ]
    return data


def team_at(snap: dict[str, Any]) -> Team:
    return Team(
        name="Clipline",
        level=snap["level"],
        capabilities=set(snap["capabilities"]),
        artifacts=set(snap["artifacts"]),
        reviewer_hours_per_week=snap["reviewer_hours_per_week"],
        agent_prs_per_week=snap["agent_prs_per_week"],
    )


def replay() -> list[tuple[str, int, int, bool, list[str]]]:
    """For each snapshot: (week, level, attempted target, allowed?, problems)."""
    out = []
    for s in snapshots():
        ok, problems = ready_for(team_at(s), s["attempt"])
        out.append((s["week"], s["level"], s["attempt"], ok, problems))
    return out


if __name__ == "__main__":
    for week, lvl, target, ok, problems in replay():
        print(f"{week}: L{lvl} -> L{target}: {'GO' if ok else 'NOT YET'}")
        for p in problems:
            print("   -", p)
