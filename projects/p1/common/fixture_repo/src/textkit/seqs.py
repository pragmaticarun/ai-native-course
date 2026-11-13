"""Sequence helpers."""


def chunk(xs: list[int], n: int) -> list[list[int]]:
    """Split xs into consecutive chunks of size n (the last may be shorter)."""
    if n <= 0:
        raise ValueError("chunk size must be positive")
    return [xs[i : i + n] for i in range(0, len(xs), n)]


def top_k(xs: list[int], k: int) -> list[int]:
    """The k largest values, largest first."""
    return sorted(xs, reverse=True)[:k]


def dedupe(xs: list[str]) -> list[str]:
    """Remove duplicates, keeping the first occurrence and the original order."""
    seen: set[str] = set()
    out = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
