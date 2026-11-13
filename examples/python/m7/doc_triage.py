"""M7 worked example: document triage graph.

router -> parallel extractors (fan-out with `Send`) -> supervisor merge -> human approval
(`interrupt`) -> file. Extractors are deterministic stand-ins for model calls so the
graph's behaviour is testable; swap them for model calls without changing the shape.
"""

from __future__ import annotations

import operator
import re
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt

EXTRACTORS = {
    "invoice": ["amount", "due_date"],
    "bug_report": ["device", "version"],
    "contract": ["parties", "due_date"],
}
PATTERNS = {
    "amount": r"(?:INR|USD|EUR)\s?[\d,]+(?:\.\d\d)?",
    "due_date": r"\b20\d\d-\d\d-\d\d\b",
    "device": r"\b(?:Galaxy|Pixel)\s[\w ]+?\b(?=,|\.|$)",
    "version": r"\bv?\d+\.\d+(?:\.\d+)?\b",
    "parties": r"between ([\w ]+?) and ([\w ]+?)(?:\.|,)",
}


class Doc(TypedDict, total=False):
    text: str
    kind: str
    fields: Annotated[list[dict[str, Any]], operator.add]
    record: dict[str, Any]
    issues: list[str]
    decision: str
    filed: str


def route(state: Doc) -> Doc:
    text = state["text"].lower()
    kind = "invoice" if "invoice" in text else "bug_report" if "crash" in text else "contract"
    return {"kind": kind}


def fan_out(state: Doc) -> list[Send]:
    return [Send("extract", {"text": state["text"], "field": f}) for f in EXTRACTORS[state["kind"]]]


def extract(task: dict[str, str]) -> Doc:
    m = re.search(PATTERNS[task["field"]], task["text"])
    if task["field"] == "parties" and m:
        value: Any = [m.group(1), m.group(2)]
    else:
        value = m.group(0) if m else None
    return {"fields": [{"field": task["field"], "value": value}]}


def supervise(state: Doc) -> Doc:
    """Merge partial results and decide what needs a human."""
    record = {f["field"]: f["value"] for f in state["fields"]}
    issues = [f"missing {k}" for k, v in record.items() if v is None]
    return {"record": record, "issues": issues}


def approve(state: Doc) -> Command:
    if not state["issues"] and state["kind"] != "contract":
        return Command(goto="file", update={"decision": "auto"})
    answer = interrupt(
        {"kind": state["kind"], "record": state["record"], "issues": state["issues"]}
    )
    return Command(goto="file" if answer == "approve" else END, update={"decision": answer})


def file(state: Doc) -> Doc:
    return {"filed": f"{state['kind']}:{sorted(state['record'].items())}"}


def build():
    g = StateGraph(Doc)
    g.add_node("route", route)
    g.add_node("extract", extract)  # type: ignore[arg-type]  # Send target: gets the payload
    g.add_node("supervise", supervise)
    g.add_node("approve", approve, destinations=("file", END))
    g.add_node("file", file)
    g.add_edge(START, "route")
    g.add_conditional_edges("route", fan_out, ["extract"])
    g.add_edge("extract", "supervise")  # fan-in: waits for every Send branch
    g.add_edge("supervise", "approve")
    g.add_edge("file", END)
    return g.compile(checkpointer=InMemorySaver())


if __name__ == "__main__":
    graph = build()
    cfg = {"configurable": {"thread_id": "inv-1"}}
    print(graph.invoke({"text": "Invoice 77: INR 12,500.00 due 2026-12-01."}, cfg)["filed"])
    cfg = {"configurable": {"thread_id": "c-1"}}
    out = graph.invoke(
        {"text": "Agreement between Acme Media and Arun Labs. Renew 2027-01-31."}, cfg
    )
    print("paused for a human:", out["__interrupt__"][0].value)
    print(graph.invoke(Command(resume="approve"), cfg)["filed"])
