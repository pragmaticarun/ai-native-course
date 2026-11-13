"""Hidden acceptance tests (the ground truth). Not part of the team repo."""

import pytest
from clipsvc.durations import format_duration, parse_duration
from clipsvc.pricing import price_cents
from clipsvc.tags import normalize_tags


def test_parse():
    assert parse_duration("1h2m3s") == 3723 and parse_duration("2m") == 120
    with pytest.raises(ValueError):
        parse_duration("2x")


def test_format():
    assert format_duration(3723) == "1:02:03" and format_duration(59) == "0:00:59"


def test_tags():
    assert normalize_tags([" News", "news", "", "  ", "Sport"]) == ["news", "sport"]


def test_price():
    assert price_cents(2.5, "pro") == 6 and price_cents(3, "studio") == 15
