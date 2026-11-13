"""L7.3: routers and classifiers. Route by intent, pick a model tier, fall back on errors.

Cheap deterministic rules run first; the model classifier is only consulted when the
rules don't match (and its answer is validated against the allowed labels).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from aincourse import AssistantTurn, Message, ScriptedModel

INTENTS = ("bug_report", "feature_request", "question")
RULES = [
    (re.compile(r"\b(crash\w*|segfault|stack trace|regression)\b", re.I), "bug_report"),
    (re.compile(r"\b(please add|would be nice|support for)\b", re.I), "feature_request"),
]


def classify(text: str, model: ScriptedModel) -> tuple[str, str]:
    """Returns (intent, how). Rules first; then the model; then a safe default."""
    for pattern, intent in RULES:
        if pattern.search(text):
            return intent, "rule"
    answer = model.complete([Message("user", f"Classify as one of {INTENTS}: {text}")]).text.strip()
    if answer in INTENTS:
        return answer, "model"
    return "question", "default"  # never route on an unvalidated label


def pick_tier(text: str) -> str:
    """Model-tier routing: long or reasoning-heavy requests go to the large tier."""
    hard = re.search(r"\b(why|design|prove|race|deadlock)\b", text, re.I)
    return "large" if hard or len(text) > 400 else "small"


class ProviderError(Exception):
    pass


def with_fallback(providers: Sequence[tuple[str, Callable[[str], str]]], prompt: str):
    """Try providers in order; return (name, answer, errors) from the first that works."""
    errors: list[str] = []
    for name, call in providers:
        try:
            return name, call(prompt), errors
        except ProviderError as exc:
            errors.append(f"{name}: {exc}")
    raise ProviderError("all providers failed: " + "; ".join(errors))


class Ticket(TypedDict, total=False):
    text: str
    intent: str
    how: str
    queue: str


def build_router(model: ScriptedModel):
    def triage(state: Ticket) -> Ticket:
        intent, how = classify(state["text"], model)
        return {"intent": intent, "how": how}

    g = StateGraph(Ticket)
    g.add_node("triage", triage)
    for intent in INTENTS:
        g.add_node(intent, lambda s, i=intent: {"queue": f"{i}-queue"})
        g.add_edge(intent, END)
    g.add_edge(START, "triage")
    g.add_conditional_edges("triage", lambda s: s["intent"], list(INTENTS))
    return g.compile()


if __name__ == "__main__":
    model = ScriptedModel([AssistantTurn(text="feature_request"), AssistantTurn(text="banana")])
    router = build_router(model)
    for text in ["App crashes on 4K HEVC", "Could we get HDR10+ metadata?", "hmm"]:
        print(text, "->", router.invoke({"text": text}))
    print(pick_tier("rename this"), pick_tier("why does this deadlock?"))
