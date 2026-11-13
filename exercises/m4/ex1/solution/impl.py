from collections.abc import Callable

PINS = ("DECISION:", "CONSTRAINT:", "FACT:")


def _pins(entries: list[str]) -> list[str]:
    return [
        line.strip() for e in entries for line in e.splitlines() if line.strip().startswith(PINS)
    ]


def compact(history: list[str], keep_last: int, summarise: Callable[[list[str]], str]) -> list[str]:
    if len(history) <= keep_last:
        return list(history)
    older, recent = history[:-keep_last], history[-keep_last:]
    summary = "\n".join(["SUMMARY: " + summarise(older), *_pins(older)])
    return [summary, *recent]


def fidelity(original: list[str], compacted: list[str]) -> float:
    pins = _pins(original)
    if not pins:
        return 1.0
    text = "\n".join(compacted)
    return sum(p in text for p in pins) / len(pins)
