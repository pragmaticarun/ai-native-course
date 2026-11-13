"""L7.6: retries, timeouts and fallbacks on graph nodes (langgraph 1.2.21 node options).

* `retry_policy=RetryPolicy(...)`: exponential backoff with jitter, only for the exception
  types you list (retrying a validation error just burns money);
* `timeout=`: the node fails with `NodeTimeoutError` if it runs too long;
* `error_handler=`: a node that turns a failure into a state update (a fallback answer).
"""

from __future__ import annotations

import asyncio
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy


class Q(TypedDict, total=False):
    question: str
    answer: str
    source: str


class RateLimited(Exception):
    pass


def build(primary, timeout_s: float = 0.2, attempts: int = 3):
    async def ask(state: Q) -> Q:
        return {"answer": await primary(state["question"]), "source": "primary"}

    def fallback(state: Q) -> Q:
        return {
            "answer": "I could not answer in time; a cached summary is attached.",
            "source": "fallback",
        }

    g = StateGraph(Q)
    g.add_node(
        "ask",
        ask,
        retry_policy=RetryPolicy(
            max_attempts=attempts, initial_interval=0.01, jitter=True, retry_on=RateLimited
        ),
        timeout=timeout_s,
        error_handler=fallback,
    )
    g.add_edge(START, "ask")
    g.add_edge("ask", END)
    return g.compile()


def flaky(fail_times: int, delay: float = 0.0):
    calls = {"n": 0}

    async def primary(question: str) -> str:
        calls["n"] += 1
        await asyncio.sleep(delay)
        if calls["n"] <= fail_times:
            raise RateLimited("429")
        return f"answer to {question!r}"

    return primary, calls


if __name__ == "__main__":
    for label, (fn, calls) in {
        "recovers after 2 x 429": flaky(2),
        "keeps failing": flaky(9),
        "too slow": flaky(0, delay=1.0),
    }.items():
        out = asyncio.run(build(fn).ainvoke({"question": "AV1 tiles?"}))
        print(f"{label:24s} -> {out['source']:8s} after {calls['n']} call(s)")
