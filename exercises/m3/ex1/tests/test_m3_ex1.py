from _impl import load

from aincourse import AssistantTurn, ScriptedModel, ToolCall

impl = load(__file__)


def read(path: str) -> str:
    if path != "README.md":
        raise FileNotFoundError(path)
    return "hello"


def brain(messages, tools):
    last = messages[-1]
    if last.role == "user" and last.content.startswith("Reflect:"):
        return AssistantTurn(tool_calls=(ToolCall("read", {"path": "README.md"}, "c2"),))
    if last.role == "tool" and not last.content.startswith("error:"):
        return AssistantTurn(text=f"README says {last.content}")
    return AssistantTurn(tool_calls=(ToolCall("read", {"path": "readme.txt"}, "c1"),))


def test_reflection_message_leads_to_recovery():
    model = ScriptedModel(brain)
    answer, reflections = impl.run_with_reflection(model, {"read": read}, "What's in the readme?")
    assert answer == "README says hello" and reflections == 1
    reflect = [m for m in model.calls[1] if m.content.startswith("Reflect:")]
    assert len(reflect) == 1 and "read" in reflect[0].content


def test_no_reflection_when_nothing_fails():
    model = ScriptedModel(
        [
            AssistantTurn(tool_calls=(ToolCall("read", {"path": "README.md"}),)),
            AssistantTurn(text="done"),
        ]
    )
    assert impl.run_with_reflection(model, {"read": read}, "x") == ("done", 0)


def test_budget():
    always_bad = ScriptedModel(lambda m, t: AssistantTurn(tool_calls=(ToolCall("nope", {}),)))
    assert impl.run_with_reflection(always_bad, {}, "x", max_steps=3) == (None, 3)
