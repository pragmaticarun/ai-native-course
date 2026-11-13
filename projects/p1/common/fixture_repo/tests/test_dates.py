import pytest
from textkit.dates import days_in_month, is_leap


def test_leap_rules():
    assert is_leap(2024)
    assert not is_leap(2023)
    assert not is_leap(1900)
    assert is_leap(2000)


def test_days_in_month():
    assert days_in_month(2024, 2) == 29
    assert days_in_month(2023, 2) == 28
    assert days_in_month(2023, 4) == 30
    assert days_in_month(2023, 12) == 31


def test_bad_month():
    with pytest.raises(ValueError):
        days_in_month(2023, 13)
