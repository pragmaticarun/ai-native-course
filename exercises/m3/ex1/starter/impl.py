from collections.abc import Callable

from aincourse import ChatModel, Message


def run_with_reflection(
    model: ChatModel, tools: dict[str, Callable[..., object]], task: str, max_steps: int = 8
) -> tuple[str | None, int]:
    # TODO: tool loop + "Reflect:" message after failed steps.
    turn = model.complete([Message("user", task)])
    return (turn.text or None, 0)
