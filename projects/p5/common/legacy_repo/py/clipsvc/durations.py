import re

UNITS = {"h": 3600, "m": 60, "s": 1}


def parse_duration(text: str) -> int:
    """'1h2m3s' -> 3723. Raises ValueError for anything else."""
    if not re.fullmatch(r"(\d+[hms])+", text):
        raise ValueError(f"bad duration {text!r}")
    return sum(int(n) * UNITS[u] for n, u in re.findall(r"(\d+)([hms])", text))


def format_duration(seconds: int) -> str:
    """3723 -> '1:02:03' (hours not padded)."""
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}"
