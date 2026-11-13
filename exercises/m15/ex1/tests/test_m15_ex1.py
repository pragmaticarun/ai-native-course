import json
from pathlib import Path

from _impl import load

impl = load(__file__)
ELS = json.loads((Path(__file__).parent / "screen.json").read_text())["elements"]
TARGETS = ["Calendar", "Title", "Date", "Time", "Save event", "Mail"] * 50


def test_annotate_reading_order_interactive_only():
    marks = impl.annotate(ELS)
    assert [e["name"] for _, e in sorted(marks.items())] == [
        "Mail",
        "Calendar",
        "Title",
        "Date",
        "Time",
        "Save event",
    ]
    assert min(marks) == 1


def test_click_point_is_the_centre():
    save = next(e for e in ELS if e["name"] == "Save event")
    assert impl.click_point(save) == (16 + 108.1 / 2, 335.8 + 17)


def test_marks_remove_invalid_actions():
    pixels = impl.invalid_rate(ELS, TARGETS, sigma_px=12, use_marks=False, seed=1)
    marks = impl.invalid_rate(ELS, TARGETS, sigma_px=12, use_marks=True, seed=1)
    assert marks == 0.0
    assert 0.2 < pixels < 0.8  # small targets (18 px links, 24 px fields) miss often at sigma 12


def test_rate_grows_with_grounding_error():
    rates = [impl.invalid_rate(ELS, TARGETS, s, use_marks=False, seed=2) for s in (0, 4, 12, 30)]
    assert rates[0] == 0.0 and rates == sorted(rates) and rates[-1] > rates[1]
