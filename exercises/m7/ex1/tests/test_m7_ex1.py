import random

import pytest
from _impl import load

impl = load(__file__)


class RateLimited(Exception):
    pass


def flaky(failures: int, exc: type[Exception] = RateLimited):
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        if calls["n"] <= failures:
            raise exc("try later")
        return "ok"

    return fn, calls


def test_delays_are_bounded_jittered_and_capped():
    d = impl.backoff_delays(6, 0.5, 4.0, random.Random(7))
    assert len(d) == 5
    for i, x in enumerate(d):
        assert 0 <= x <= min(4.0, 0.5 * 2**i)
    assert len(set(d)) == 5  # jittered, not a fixed ladder
    assert d == impl.backoff_delays(6, 0.5, 4.0, random.Random(7))  # reproducible


def test_retries_then_succeeds_with_the_same_delays():
    fn, calls = flaky(2)
    slept: list[float] = []
    out = impl.retry(fn, attempts=4, base=1, cap=10, rng=random.Random(1), sleep=slept.append,
                     retry_on=(RateLimited,))  # fmt: skip
    assert out == "ok" and calls["n"] == 3
    assert slept == impl.backoff_delays(4, 1, 10, random.Random(1))[:2]


def test_gives_up_and_reraises():
    fn, calls = flaky(10)
    slept: list[float] = []
    with pytest.raises(RateLimited):
        impl.retry(fn, attempts=3, base=1, cap=10, rng=random.Random(1), sleep=slept.append,
                   retry_on=(RateLimited,))  # fmt: skip
    assert calls["n"] == 3 and len(slept) == 2


def test_does_not_retry_other_errors():
    fn, calls = flaky(1, ValueError)
    slept: list[float] = []
    with pytest.raises(ValueError):
        impl.retry(fn, attempts=5, base=1, cap=10, rng=random.Random(1), sleep=slept.append,
                   retry_on=(RateLimited,))  # fmt: skip
    assert calls["n"] == 1 and slept == []
