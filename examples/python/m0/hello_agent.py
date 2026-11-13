"""M0 worked example: the smallest possible "agent" call, mock first.

Run:  uv run python ../examples/python/m0/hello_agent.py
Live: COURSE_LLM_PROVIDER=openai COURSE_LLM_MODEL=<model> uv run --extra live python ...
"""

from __future__ import annotations

import sys

from aincourse import AssistantTurn, Message, get_model

SYSTEM = "You are a terse assistant for systems engineers."


def hello(name: str) -> str:
    model = get_model([AssistantTurn(text=f"Hello, {name}! (mock model, no network used)")])
    turn = model.complete([Message("system", SYSTEM), Message("user", f"Say hello to {name}.")])
    return turn.text


if __name__ == "__main__":
    print(hello(sys.argv[1] if len(sys.argv) > 1 else "Arunkumar"))
