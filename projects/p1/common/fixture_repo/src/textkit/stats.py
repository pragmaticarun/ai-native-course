"""Small statistics helpers."""


def mean(xs: list[float]) -> float:
    """Arithmetic mean. Raises ValueError on an empty list."""
    if not xs:
        raise ValueError("mean of empty list")
    return sum(xs) / len(xs)


def variance(xs: list[float]) -> float:
    """Sample variance (n - 1 in the denominator). Needs at least two values."""
    n = len(xs)
    if n < 2:
        raise ValueError("variance needs at least two values")
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (n - 1)


def clamp(x: float, lo: float, hi: float) -> float:
    """Limit x to the closed interval [lo, hi]."""
    return max(lo, min(x, hi))
