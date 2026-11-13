import random
from collections.abc import Callable


def backoff_delays(attempts: int, base: float, cap: float, rng: random.Random) -> list[float]:
    return [rng.uniform(0, min(cap, base * 2**i)) for i in range(attempts - 1)]


def retry[T](
    fn: Callable[[], T],
    *,
    attempts: int,
    base: float,
    cap: float,
    rng: random.Random,
    sleep: Callable[[float], None],
    retry_on: tuple[type[BaseException], ...],
) -> T:
    delays = backoff_delays(attempts, base, cap, rng)
    for i in range(attempts):
        try:
            return fn()
        except retry_on:
            if i == attempts - 1:
                raise
            sleep(delays[i])
    raise AssertionError("unreachable")
