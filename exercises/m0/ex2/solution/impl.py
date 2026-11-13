from collections.abc import Sequence

from aincourse import AssistantTurn, Message, ScriptedModel, ToolCall, ToolSpec


def make_scripted_model() -> ScriptedModel:
    def brain(messages: Sequence[Message], tools: Sequence[ToolSpec]) -> AssistantTurn:
        last = messages[-1]
        if last.role == "tool":
            return AssistantTurn(text=f"It is {last.content} in Kolkata.")
        return AssistantTurn(tool_calls=(ToolCall("get_time", {"tz": "Asia/Kolkata"}, "c1"),))

    return ScriptedModel(brain)
