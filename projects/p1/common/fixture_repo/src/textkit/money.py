"""Money helpers. Amounts are integer cents."""


def apply_discount(cents: int, pct: float) -> int:
    """Price after a percentage discount, rounded to the nearest cent."""
    return round(cents * (1 - pct / 100))


def split_bill(cents: int, people: int) -> list[int]:
    """Split a bill into `people` shares that differ by at most one cent; earlier
    people pay the extra cents."""
    base, remainder = divmod(cents, people)
    return [base + 1 if i < remainder else base for i in range(people)]
