from collections.abc import Callable

Model = Callable[[str], str]


def three_agent(facts: list[str], model: Model) -> tuple[str, int]:
    """researcher -> writer -> reviewer. Each brief keeps only the first 3 items."""
    research = model("Research: " + "; ".join(facts))
    brief = "; ".join(research.split("; ")[:3])  # lossy hand-off
    draft = model("Write: " + brief)
    final = model("Review: " + draft)
    return final, 3


def single_agent(facts: list[str], model: Model) -> tuple[str, int]:
    # TODO
    return "", 0


def score(text: str, facts: list[str]) -> float:
    # TODO
    return 0.0


def compare(cases: list[list[str]], model: Model) -> dict[str, dict[str, float]]:
    # TODO
    return {}
