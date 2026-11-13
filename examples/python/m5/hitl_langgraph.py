"""L5.4: interrupt and resume with LangGraph (`interrupt` + a checkpointer).

The graph drafts, then pauses at `approve` until a human resumes it with a
decision. The checkpointer keeps the paused state, so the resume can happen in
another process or hours later (with a durable saver; InMemorySaver here).
Tested with langgraph 1.2.21 (pinned in python/pyproject.toml).
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class State(TypedDict, total=False):
    recording: str
    plan: str
    approved: bool
    reason: str
    result: str


def plan(state: State) -> State:
    return {"plan": f"delete_recording({state['recording']!r})"}


def approve(state: State) -> State:
    decision = interrupt({"question": "Run this destructive action?", "action": state["plan"]})
    return {"approved": bool(decision.get("approved")), "reason": decision.get("reason", "")}


def act(state: State) -> State:
    if not state.get("approved"):
        return {"result": f"skipped: {state.get('reason') or 'not approved'}"}
    return {"result": f"deleted {state['recording']}"}


def build():
    g = StateGraph(State)
    g.add_node("plan", plan)
    g.add_node("approve", approve)
    g.add_node("act", act)
    g.add_edge(START, "plan")
    g.add_edge("plan", "approve")
    g.add_edge("approve", "act")
    g.add_edge("act", END)
    return g.compile(checkpointer=InMemorySaver())


def start(graph, thread: str, recording: str) -> dict:
    """Runs until the interrupt; returns the interrupt payload shown to the human."""
    out = graph.invoke({"recording": recording}, {"configurable": {"thread_id": thread}})
    return out["__interrupt__"][0].value


def resume(graph, thread: str, approved: bool, reason: str) -> str:
    out = graph.invoke(
        Command(resume={"approved": approved, "reason": reason}),
        {"configurable": {"thread_id": thread}},
    )
    return out["result"]


if __name__ == "__main__":
    graph = build()
    print(start(graph, "t1", "meeting-2026-11-13.m4a"))
    print(resume(graph, "t1", approved=True, reason="duplicate of the uploaded copy"))
