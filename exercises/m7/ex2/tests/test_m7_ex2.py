import inspect

from _impl import load

from aincourse.llm import AssistantTurn, ScriptedModel

impl = load(__file__)

LINES = [
    "fix: crash when the clip is empty",
    "feat: export chapters",
    "docs: typo",
    "fix: audio drift after 1h",
    "feat: dark mode",
]
GOLD = ["bug", "feature", "chore", "bug", "feature"]


def make_model() -> ScriptedModel:
    """Labels lines by prefix. As a planner it gets bored and says done after 3 lines."""

    def script(messages, tools):
        text = messages[-1].content
        if text.startswith("classify: "):
            prefix = text.removeprefix("classify: ").split(":")[0]
            return AssistantTurn(text={"fix": "bug", "feat": "feature"}.get(prefix, "chore"))
        done = int(text.split("done=")[1])
        return AssistantTurn(text="done" if done >= 3 else f"classify {done}")

    return ScriptedModel(script)


def test_graph_labels_every_line_with_one_call_each():
    out = impl.graph_triage(make_model(), LINES)
    assert out["labels"] == GOLD
    assert out["calls"] == len(LINES)


def test_graph_triage_uses_langgraph():
    src = inspect.getsource(impl.graph_triage)
    assert "StateGraph" in src and "freeform_triage" not in src


def test_compare():
    r = impl.compare(make_model, LINES, GOLD)
    assert r["graph"] == {"accuracy": 1.0, "calls": 5}
    assert r["freeform"] == {"accuracy": 0.6, "calls": 7}  # 4 plans + 3 classifications
