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
    return model("Write: " + "; ".join(facts)), 1


def score(text: str, facts: list[str]) -> float:
    if not facts:
        return 1.0
    low = text.lower()
    return sum(f.lower() in low for f in facts) / len(facts)


def compare(cases: list[list[str]], model: Model) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for name, design in (("three_agent", three_agent), ("single_agent", single_agent)):
        scores, calls = [], 0
        for facts in cases:
            text, n = design(facts, model)
            scores.append(score(text, facts))
            calls += n
        out[name] = {"score": sum(scores) / len(scores), "calls": calls}
    return out
