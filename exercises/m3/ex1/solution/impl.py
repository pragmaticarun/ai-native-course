from collections.abc import Callable

from aincourse import ChatModel, Message


def run_with_reflection(
    model: ChatModel, tools: dict[str, Callable[..., object]], task: str, max_steps: int = 8
) -> tuple[str | None, int]:
    messages = [Message("user", task)]
    reflections = 0
    for _ in range(max_steps):
        turn = model.complete(messages)
        if not turn.tool_calls:
            return turn.text, reflections
        messages.append(turn.as_message())
        failed: list[str] = []
        for call in turn.tool_calls:
            fn = tools.get(call.name)
            try:
                if fn is None:
                    raise LookupError(f"no tool named {call.name!r}")
                result = str(fn(**call.arguments))
            except Exception as err:
                result = f"error: {type(err).__name__}: {err}"
                failed.append(call.name)
            messages.append(Message("tool", result, tool_call_id=call.id))
        if failed:
            reflections += 1
            messages.append(
                Message(
                    "user",
                    f"Reflect: {', '.join(failed)} failed. Say why, then try a different approach.",
                )
            )
    return None, reflections
