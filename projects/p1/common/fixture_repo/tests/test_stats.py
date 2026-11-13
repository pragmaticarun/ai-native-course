import pytest
from textkit.stats import clamp, mean, variance


def test_mean_basic():
    assert mean([1, 2, 3, 4]) == 2.5


def test_mean_single():
    assert mean([7]) == 7


def test_mean_empty():
    with pytest.raises(ValueError):
        mean([])


def test_variance_sample():
    assert variance([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(32 / 7)


def test_variance_two():
    assert variance([1, 3]) == 2


def test_clamp_inside_and_edges():
    assert clamp(5, 0, 10) == 5
    assert clamp(-3, 0, 10) == 0
    assert clamp(42, 0, 10) == 10
