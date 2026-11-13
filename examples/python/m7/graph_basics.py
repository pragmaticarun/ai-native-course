"""L7.1-L7.2: from a free-form loop to an explicit graph, and what reducers do.

The same three-step job ("fetch a changelog, classify each line, render notes") is
written twice: as a model-driven loop that asks the model what to do next on every
turn, and as a LangGraph `StateGraph` where only the classification step uses the
model. Reducers decide how parallel or repeated writes to one state key combine.
Tested with langgraph 1.2.21 (pinned in python/pyproject.toml).
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from aincourse import AssistantTurn, Message, ScriptedModel, ToolCall

CHANGELOG = ["feat: AV1 decode", "fix: crash on empty playlist", "chore: bump deps"]


# ----------------------------------------------------------------------------- free-form loop


def free_form(model: ScriptedModel, max_turns: int = 10) -> str:
    """The model picks every step, so every step costs a model call (and can go wrong)."""
    tools: dict[str, Callable[..., str]] = {
        "fetch": lambda: "\n".join(CHANGELOG),
        "classify": lambda line: "feature" if line.startswith("feat") else "other",
    }
    messages = [Message("user", "Write release notes from the changelog.")]
    for _ in range(max_turns):
        turn = model.complete(messages)
        messages.append(turn.as_message())
        if not turn.tool_calls:
            return turn.text
        for call in turn.tool_calls:
            messages.append(
                Message("tool", tools[call.name](**call.arguments), tool_call_id=call.id)
            )
    return ""


def scripted_free_form() -> ScriptedModel:
    calls = [AssistantTurn(tool_calls=(ToolCall("fetch", {}),))]
    calls += [
        AssistantTurn(tool_calls=(ToolCall("classify", {"line": line}),)) for line in CHANGELOG
    ]
    calls.append(AssistantTurn(text="Features: AV1 decode"))
    return ScriptedModel(calls)


# ----------------------------------------------------------------------------- explicit graph


class NotesState(TypedDict, total=False):
    lines: list[str]
    labels: Annotated[list[str], operator.add]  # reducer: append, don't overwrite
    notes: str


def build_notes_graph(classify: Callable[[str], str]):
    def fetch(state: NotesState) -> NotesState:
        return {"lines": list(CHANGELOG)}

    def label(state: NotesState) -> NotesState:
        return {"labels": [classify(line) for line in state["lines"]]}

    def render(state: NotesState) -> NotesState:
        feats = [
            line.split(": ", 1)[1]
            for line, lab in zip(state["lines"], state["labels"], strict=True)
            if lab == "feature"
        ]
        return {"notes": "Features: " + "; ".join(feats)}

    g = StateGraph(NotesState)
    g.add_node("fetch", fetch)
    g.add_node("label", label)
    g.add_node("render", render)
    g.add_edge(START, "fetch")
    g.add_edge("fetch", "label")
    g.add_edge("label", "render")
    g.add_edge("render", END)
    return g.compile()


# ----------------------------------------------------------------------------- reducers


def merge_latest(left: dict[str, tuple[int, str]], right: dict[str, tuple[int, str]]):
    """A last-writer-wins map keyed by field, using a version number: CRDT-style merge.

    Commutative and idempotent, so parallel branches can write in any order."""
    out = dict(left)
    for key, (version, value) in right.items():
        if key not in out or version > out[key][0]:
            out[key] = (version, value)
    return out


class Facts(TypedDict, total=False):
    facts: Annotated[dict[str, tuple[int, str]], merge_latest]


def build_parallel_writers():
    g = StateGraph(Facts)
    g.add_node("probe", lambda s: {"facts": {"codec": (1, "h264"), "fps": (1, "30")}})
    g.add_node("asr", lambda s: {"facts": {"language": (1, "en"), "fps": (2, "29.97")}})
    g.add_edge(START, "probe")
    g.add_edge(START, "asr")  # both run in the same super-step
    g.add_edge("probe", END)
    g.add_edge("asr", END)
    return g.compile()


if __name__ == "__main__":
    loop_model = scripted_free_form()
    print("free-form:", free_form(loop_model), "| model calls:", len(loop_model.calls))
    graph_calls: list[str] = []

    def classify(line: str) -> str:
        graph_calls.append(line)  # stand-in for one cheap classification call per line
        return "feature" if line.startswith("feat") else "other"

    print(
        "graph:",
        build_notes_graph(classify).invoke({})["notes"],
        "| model calls:",
        len(graph_calls),
    )
    print("merged facts:", build_parallel_writers().invoke({"facts": {}})["facts"])
