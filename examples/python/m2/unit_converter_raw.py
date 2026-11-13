"""L2.4 worked example: tool calling end to end, no framework.

schema -> model picks a tool -> we execute it -> result goes back -> model answers.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from aincourse import AssistantTurn, ChatModel, Message, ScriptedModel, ToolCall, ToolSpec

FACTORS = {
    ("km", "mi"): 0.621371,
    ("mi", "km"): 1.609344,
    ("kg", "lb"): 2.204623,
    ("lb", "kg"): 0.453592,
}

CONVERT = ToolSpec(
    name="convert",
    description="Convert a value between units. Supported: km<->mi, kg<->lb.",
    parameters={
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "from_unit": {"type": "string"},
            "to_unit": {"type": "string"},
        },
        "required": ["value", "from_unit", "to_unit"],
        "additionalProperties": False,
    },
)


def convert(value: float, from_unit: str, to_unit: str) -> float:
    try:
        return round(value * FACTORS[(from_unit, to_unit)], 4)
    except KeyError:
        raise ValueError(f"unsupported conversion {from_unit}->{to_unit}") from None


def run_tool(call: ToolCall) -> str:
    if call.name != "convert":
        return f"error: unknown tool {call.name!r}"
    try:
        return str(convert(**call.arguments))
    except (TypeError, ValueError) as err:  # errors go back to the model as text
        return f"error: {err}"


def ask(model: ChatModel, question: str) -> str:
    messages = [
        Message("system", "Use the convert tool for unit conversions."),
        Message("user", question),
    ]
    turn = model.complete(messages, [CONVERT])
    while turn.tool_calls:
        messages.append(turn.as_message())
        for call in turn.tool_calls:
            messages.append(Message("tool", run_tool(call), tool_call_id=call.id))
        turn = model.complete(messages, [CONVERT])
    return turn.text


def scripted_brain(messages: Sequence[Message], tools: Sequence[ToolSpec]) -> AssistantTurn:
    """A fake model: call the tool once, then phrase the tool result."""
    last = messages[-1]
    if last.role == "tool":
        return AssistantTurn(text=f"That is {last.content} miles.")
    args: dict[str, Any] = {"value": 42.195, "from_unit": "km", "to_unit": "mi"}
    return AssistantTurn(tool_calls=(ToolCall("convert", args, "call_1"),))


if __name__ == "__main__":
    print(ask(ScriptedModel(scripted_brain), "How many miles is a marathon (42.195 km)?"))
