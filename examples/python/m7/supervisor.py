"""L7.5: a supervisor over worker subgraphs, with shared vs private state.

Each worker is its own compiled graph with a private `scratch` key that never reaches the
parent. The supervisor hands off with `Command`.

Pitfall shown by `build(naive=True)`: adding a subgraph directly as a node passes it the
parent's keys, including the whole `log`. The subgraph returns that list, and the parent's
`operator.add` reducer appends it again, so entries are duplicated. The fix is an explicit
boundary: call the worker with only what it needs and return only what it produced.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


class Shared(TypedDict, total=False):
    task: str
    log: Annotated[list[str], operator.add]


class WorkerState(Shared, total=False):
    scratch: list[str]  # private to the worker subgraph


def make_worker(name: str, steps: list[str]):
    def think(state: WorkerState) -> WorkerState:
        return {"scratch": [f"{name} considered {s}" for s in steps]}

    def report(state: WorkerState) -> WorkerState:
        return {"log": [f"{name}: {len(state['scratch'])} notes on {state['task']!r}"]}

    g = StateGraph(WorkerState)
    g.add_node("think", think)
    g.add_node("report", report)
    g.add_edge(START, "think")
    g.add_edge("think", "report")
    g.add_edge("report", END)
    return g.compile()


PLAN = ["researcher", "writer"]


def supervisor(state: Shared) -> Command:
    done = {line.split(":")[0] for line in state.get("log", [])}
    for worker in PLAN:
        if worker not in done:
            return Command(goto=worker, update={"log": [f"supervisor -> {worker}"]})
    return Command(goto=END)


WORKERS = {
    "researcher": make_worker("researcher", ["codecs", "containers"]),
    "writer": make_worker("writer", ["outline", "draft", "polish"]),
}


def bounded(name: str):
    """Explicit boundary: the worker sees only the task and returns only its own log."""

    def node(state: Shared) -> Shared:
        out = WORKERS[name].invoke({"task": state["task"]})
        return {"log": out["log"]}

    return node


def build(naive: bool = False):
    g = StateGraph(Shared)
    g.add_node("supervisor", supervisor, destinations=(*PLAN, END))
    for name in PLAN:
        g.add_node(name, WORKERS[name] if naive else bounded(name))
    g.add_edge(START, "supervisor")
    for worker in PLAN:
        g.add_edge(worker, "supervisor")
    return g.compile()


if __name__ == "__main__":
    out = build().invoke({"task": "AV1 vs HEVC for 4K uploads"})
    print("\n".join(out["log"]))
    print("scratch leaked to parent:", "scratch" in out)
    print(
        "naive log length:",
        len(build(naive=True).invoke({"task": "x"})["log"]),
        "vs",
        len(out["log"]),
    )
