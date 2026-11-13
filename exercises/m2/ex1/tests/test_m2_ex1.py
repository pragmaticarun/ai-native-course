import pytest
from _impl import load

from aincourse import AssistantTurn, ScriptedModel, ToolCall

impl = load(__file__)


def brain(bad_first: int):
    def decide(messages, tools):
        tool_msgs = [m for m in messages if m.role == "tool"]
        if tool_msgs and not tool_msgs[-1].content.startswith("error:"):
            return AssistantTurn(text=f"= {tool_msgs[-1].content} mi")
        if len(tool_msgs) < bad_first:
            return AssistantTurn(
                tool_calls=(
                    ToolCall(
                        "convert", {"value": "ten", "from_unit": "km", "to_unit": "miles"}, "c"
                    ),
                )
            )
        return AssistantTurn(
            tool_calls=(
                ToolCall("convert", {"value": 10, "from_unit": "km", "to_unit": "mi"}, "c"),
            )
        )

    return decide


def test_valid_first_time():
    assert impl.convert_with_repair(ScriptedModel(brain(0)), "10 km?") == "= 6.2137 mi"


def test_repairs_after_errors_are_sent_back():
    model = ScriptedModel(brain(2))
    assert impl.convert_with_repair(model, "10 km?") == "= 6.2137 mi"
    tool_results = [m.content for m in model.calls[-1] if m.role == "tool"]
    assert tool_results[0].startswith("error:") and tool_results[1].startswith("error:")


def test_gives_up():
    with pytest.raises(RuntimeError):
        impl.convert_with_repair(ScriptedModel(brain(99)), "10 km?", max_attempts=3)
