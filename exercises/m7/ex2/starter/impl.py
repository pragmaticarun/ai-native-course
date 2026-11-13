from collections.abc import Callable
from typing import Any

from aincourse.llm import Message, ScriptedModel


def freeform_triage(model: ScriptedModel, lines: list[str]) -> dict[str, Any]:
    """Given (complete). The model plans each step, then classifies one line."""
    labels: list[str | None] = [None] * len(lines)
    for _ in range(2 * len(lines) + 2):
        plan = model.complete([Message("user", f"next? done={sum(x is not None for x in labels)}")])
        if plan.text.startswith("done"):
            break
        i = int(plan.text.split()[1])
        labels[i] = model.complete([Message("user", f"classify: {lines[i]}")]).text
    return {"labels": labels, "calls": len(model.calls)}


def graph_triage(model: ScriptedModel, lines: list[str]) -> dict[str, Any]:
    # TODO: build a LangGraph StateGraph that classifies every line
    return freeform_triage(model, lines)


def compare(
    make_model: Callable[[], ScriptedModel], lines: list[str], gold: list[str]
) -> dict[str, dict[str, float]]:
    # TODO
    return {"freeform": {"accuracy": 0.0, "calls": 0}, "graph": {"accuracy": 0.0, "calls": 0}}
