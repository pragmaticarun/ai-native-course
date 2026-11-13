import time

import pytest
from clipsvc.durations import format_duration, parse_duration


def test_parse_units():
    assert parse_duration("1h") == 3600
    assert parse_duration("2m") == 120
    assert parse_duration("1h2m3s") == 3723


def test_parse_rejects_junk():
    with pytest.raises(ValueError):
        parse_duration("2x")


def test_format_pads_minutes_and_seconds_not_hours():
    assert format_duration(3723) == "1:02:03"
    assert format_duration(59) == "0:00:59"


@pytest.mark.slow
def test_parse_against_staging():
    time.sleep(2)  # "integration": pretends to call the staging API
    assert parse_duration("2m") == 120
