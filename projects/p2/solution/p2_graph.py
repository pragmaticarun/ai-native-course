"""P2 milestones 1, 2 and 4: the research graph.

    supervisor ──(no topics)──────────────────────────────▶ no_evidence ─▶ END
        │ Send × k (one per sub-question; parallel, retried)
        ▼
    research ×k ─▶ write ─▶ critic ─(bad & revisions < cap)─▶ write
                              │
                              └──▶ approve (interrupt: a human decides) ─▶ publish ─▶ END
                                                                        └▶ END (rejected)

* supervisor: decomposes the question into sub-questions and routes them;
* research: one worker per sub-question (fan-out with `Send`, fan-in at `write`);
  searches, drops documents from other years, extracts claims; `RetryPolicy` retries
  transient search errors;
* write → critic: reflection with a cap (`max_revisions`); after the cap the draft goes
  to the human *with* the critic's notes instead of looping forever;
* approve: `interrupt()` pauses with the report and notes; resume with "approve",
  "reject" or {"edit": "..."}; the checkpointer makes the pause survive a restart.
"""

from __future__ import annotations

import operator
import re
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, Send, interrupt
from opentelemetry.trace import Tracer
from p2_critic import critique
from p2_kit import MockLLM, Search, TransientSearchError
from p2_tracing import memory_tracer, traced


class State(TypedDict, total=False):
    question: str
    subqs: list[dict[str, str]]
    findings: Annotated[list[dict[str, Any]], operator.add]
    draft: list[dict[str, str]]
    bad: list[int]
    notes: list[str]
    revisions: int
    decision: str
    report: str
    published: bool


def render(draft: list[dict[str, str]], notes: list[str] | None = None) -> str:
    body = " ".join(f"{d['text']} [{d['cite']}]" for d in draft)
    if notes:
        body += "\n\nReviewer notes: " + "; ".join(notes)
    return body


def build(
    llm: MockLLM,
    search: Search,
    *,
    tracer: Tracer | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    max_revisions: int = 2,
    claims_per_topic: int = 4,
    claims_per_doc: int = 2,
) -> Any:
    tracer = tracer or memory_tracer()[0]
    t = lambda name: traced(tracer, name, llm.usage)  # noqa: E731

    @t("supervisor")
    def supervisor(state: State) -> State:
        return {"subqs": llm.decompose(state["question"]), "revisions": 0}

    def route(state: State) -> list[Send] | str:
        if not state["subqs"]:
            return "no_evidence"
        return [Send("research", {**sq, "question": state["question"]}) for sq in state["subqs"]]

    @t("research")
    def research(task: dict[str, str]) -> State:
        year = re.findall(r"\b20\d\d\b", task["question"])
        claims: list[dict[str, str]] = []
        for doc in search(f"{task['topic']} {task['q']}", k=4):
            if year and re.findall(r"\b20\d\d\b", doc["text"]) and year[0] not in doc["text"]:
                continue  # an outdated report: right topic, wrong year
            found = llm.extract(task, doc)[:claims_per_doc]  # spread claims across sources
            claims += [{"text": s, "doc": doc["id"]} for s in found]
        return {"findings": [{"topic": task["topic"], "q": task["q"],
                              "claims": claims[:claims_per_topic]}]}  # fmt: skip

    @t("write")
    def write(state: State) -> State:
        # Fan-in: workers can find the same sentence (tram and budget both cite the tram
        # budget); merge before writing so the report says it once.
        seen: set[tuple[str, str]] = set()
        merged = []
        for f in state["findings"]:
            claims = [c for c in f["claims"] if (c["text"], c["doc"]) not in seen]
            seen |= {(c["text"], c["doc"]) for c in claims}
            merged.append({**f, "claims": claims})
        draft = llm.write(state["question"], merged, state.get("bad"))
        return {"draft": draft}

    @t("critic")
    def critic(state: State) -> Command[Any]:
        c = critique(state["draft"], state["subqs"], state["findings"])
        if c.bad and state["revisions"] < max_revisions:
            return Command(goto="write", update={"bad": c.bad, "notes": c.notes,
                                                 "revisions": state["revisions"] + 1})  # fmt: skip
        return Command(goto="approve", update={"bad": c.bad, "notes": c.notes})

    def approve(state: State) -> Command[Any]:
        report = render(state["draft"], state.get("notes"))
        answer = interrupt({"report": report, "notes": state.get("notes", []),
                            "revisions": state["revisions"]})  # fmt: skip
        if isinstance(answer, dict) and "edit" in answer:
            return Command(goto="publish", update={"decision": "edited", "report": answer["edit"]})
        if answer == "approve":
            return Command(goto="publish", update={"decision": "approved", "report": report})
        return Command(goto=END, update={"decision": "rejected", "report": report})

    @t("publish")
    def publish(state: State) -> State:
        return {"published": True}

    @t("no_evidence")
    def no_evidence(state: State) -> State:
        return {"report": "No sources in the corpus cover this question.", "published": False}

    g = StateGraph(State)
    g.add_node("supervisor", supervisor)
    retry = RetryPolicy(
        retry_on=TransientSearchError, max_attempts=3, initial_interval=0.01, jitter=False
    )
    g.add_node("research", research, retry_policy=retry)  # type: ignore[arg-type]
    g.add_node("write", write)
    g.add_node("critic", critic, destinations=("write", "approve"))
    g.add_node("approve", approve, destinations=("publish", END))
    g.add_node("publish", publish)
    g.add_node("no_evidence", no_evidence)
    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", route, ["research", "no_evidence"])
    g.add_edge("research", "write")
    g.add_edge("write", "critic")
    g.add_edge("publish", END)
    g.add_edge("no_evidence", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())
