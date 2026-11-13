from collections.abc import Callable

PINS = ("DECISION:", "CONSTRAINT:", "FACT:")


def compact(history: list[str], keep_last: int, summarise: Callable[[list[str]], str]) -> list[str]:
    # TODO: keep pinned lines verbatim. This version loses them.
    older, recent = history[:-keep_last], history[-keep_last:]
    return ["SUMMARY: " + summarise(older), *recent]


def fidelity(original: list[str], compacted: list[str]) -> float:
    # TODO: measure it instead of assuming it.
    return 1.0
