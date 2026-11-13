from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

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


class Triage(TypedDict, total=False):
    lines: list[str]
    labels: list[str]
    groups: dict[str, list[str]]


def graph_triage(model: ScriptedModel, lines: list[str]) -> dict[str, Any]:
    def classify(state: Triage) -> Triage:
        return {
            "labels": [
                model.complete([Message("user", f"classify: {ln}")]).text for ln in state["lines"]
            ]
        }

    def group(state: Triage) -> Triage:
        groups: dict[str, list[str]] = {}
        for ln, lab in zip(state["lines"], state["labels"], strict=True):
            groups.setdefault(lab, []).append(ln)
        return {"groups": groups}

    g = StateGraph(Triage)
    g.add_node("classify", classify)
    g.add_node("group", group)
    g.add_edge(START, "classify")
    g.add_edge("classify", "group")
    g.add_edge("group", END)
    out = g.compile().invoke({"lines": lines})
    return {"labels": out["labels"], "calls": len(model.calls)}


def _accuracy(labels: list[Any], gold: list[str]) -> float:
    return sum(a == b for a, b in zip(labels, gold, strict=True)) / len(gold)


def compare(
    make_model: Callable[[], ScriptedModel], lines: list[str], gold: list[str]
) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for name, fn in (("freeform", freeform_triage), ("graph", graph_triage)):
        r = fn(make_model(), lines)
        out[name] = {"accuracy": _accuracy(r["labels"], gold), "calls": r["calls"]}
    return out
