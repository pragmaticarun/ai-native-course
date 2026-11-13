"""Calendar helpers (Gregorian)."""


def is_leap(year: int) -> bool:
    """Leap year: divisible by 4, except centuries, except every 400 years."""
    return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0


def days_in_month(year: int, month: int) -> int:
    """Days in a month (1-12)."""
    if not 1 <= month <= 12:
        raise ValueError(f"bad month {month}")
    if month == 2:
        return 29 if is_leap(year) else 28
    return 30 if month in (4, 6, 9, 11) else 31
