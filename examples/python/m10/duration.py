"""The implementation an agent produced from specs/001-duration-parse/spec.md."""

from __future__ import annotations

import re

PATTERN = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")


def parse_duration(text: str) -> int:
    m = PATTERN.match(text)
    if not text or not m:
        raise ValueError(f"not a duration: {text!r} (use e.g. 1h30m, 45s)")
    h, mi, s = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mi * 60 + s


def parse_duration_buggy(text: str) -> int:
    """A plausible first attempt: sums units in any order and treats '' as 0."""
    total = 0
    for n, unit in re.findall(r"(\d+)([hms])", text):
        total += int(n) * {"h": 3600, "m": 60, "s": 1}[unit]
    if re.sub(r"\d+[hms]", "", text):
        raise ValueError(text)
    return total
