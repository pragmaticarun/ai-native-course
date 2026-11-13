"""L3.5: detectors for classic agent failure modes, run over a tool-call trace."""

from __future__ import annotations

import json
from collections.abc import Iterable

from aincourse import ToolCall


def repeated_calls(calls: Iterable[ToolCall], threshold: int = 3) -> list[str]:
    """Same tool with the same arguments `threshold`+ times in a row = thrashing."""
    hits, run, prev = [], 0, None
    for c in calls:
        key = f"{c.name}:{json.dumps(c.arguments, sort_keys=True)}"
        run = run + 1 if key == prev else 1
        prev = key
        if run == threshold:
            hits.append(key)
    return hits


def hallucinated_tools(calls: Iterable[ToolCall], known: set[str]) -> list[str]:
    return sorted({c.name for c in calls if c.name not in known})


def premature_done(claimed_done: bool, verified: bool) -> bool:
    """The agent said it was done but the state check disagrees."""
    return claimed_done and not verified
