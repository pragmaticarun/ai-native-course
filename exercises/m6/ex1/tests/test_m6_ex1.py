import re

from _impl import load

impl = load(__file__)

# Ten release-note entries: the judge's 1-5 scores and a human's pass/fail.
JUDGE = [5, 4, 4, 3, 5, 2, 3, 4, 1, 5]
HUMAN = [True, True, False, False, True, False, False, True, False, True]


def test_rubric_has_anchors():
    for s in "12345":
        assert re.search(rf"(^|\n)\s*{s}\s*:", impl.RUBRIC), f"missing anchor for {s}"


def test_kappa():
    assert impl.cohen_kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert (
        abs(impl.cohen_kappa([True, True, False, False], [True, False, True, False]) - 0.0) < 1e-9
    )
    assert impl.cohen_kappa([True] * 3, [True] * 3) == 1.0


def test_calibration_picks_threshold_4():
    t, k = impl.calibrate(JUDGE, HUMAN)
    assert t == 4
    assert abs(k - 0.8) < 1e-9  # one disagreement in ten at t=4
