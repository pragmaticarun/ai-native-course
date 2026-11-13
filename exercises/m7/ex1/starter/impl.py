import random
from collections.abc import Callable


def backoff_delays(attempts: int, base: float, cap: float, rng: random.Random) -> list[float]:
    # TODO: full jitter, one delay per retry
    return [base] * attempts


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
    # TODO: retry only on retry_on, sleep between attempts, re-raise the last error
    return fn()
