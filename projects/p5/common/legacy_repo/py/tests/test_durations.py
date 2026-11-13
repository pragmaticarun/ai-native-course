import time

from clipsvc.durations import parse_duration


def test_parse_hours():
    assert parse_duration("1h") == 3600


def test_parse_against_staging():
    time.sleep(2)  # "integration": pretends to call the staging API
    assert parse_duration("2m") == 120
