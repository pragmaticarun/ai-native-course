"""L3.2: an agent loop from scratch (no framework).

perceive -> plan -> act -> observe, until the model answers in text, the step
budget runs out, or the same call repeats too often. Tool errors are fed back
to the model as observations instead of crashing the loop.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aincourse import ChatModel, Message, ToolCall, ToolSpec

ToolFn = Callable[..., Any]


@dataclass
class Tool:
    spec: ToolSpec
    fn: ToolFn


@dataclass
class RunResult:
    answer: str | None
    stop_reason: str  # "answered" | "max_steps" | "repetition"
    steps: int
    trace: list[str] = field(default_factory=list)


def execute(tools: dict[str, Tool], call: ToolCall) -> str:
    tool = tools.get(call.name)
    if tool is None:  # hallucinated tool: tell the model what exists
        return f"error: no tool named {call.name!r}; available: {sorted(tools)}"
    try:
        return str(tool.fn(**call.arguments))
    except Exception as err:  # error-as-observation
        return f"error: {type(err).__name__}: {err}"


def run_agent(
    model: ChatModel,
    tools: dict[str, Tool],
    task: str,
    system: str = "",
    max_steps: int = 8,
    max_repeats: int = 3,
) -> RunResult:
    messages = [Message("system", system or "Use tools, then answer."), Message("user", task)]
    specs = [t.spec for t in tools.values()]
    seen: Counter[str] = Counter()
    trace: list[str] = []
    for step in range(1, max_steps + 1):
        turn = model.complete(messages, specs)  # plan
        if not turn.tool_calls:  # stop condition: final answer
            return RunResult(turn.text, "answered", step, trace)
        messages.append(turn.as_message())
        for call in turn.tool_calls:  # act
            key = f"{call.name}:{json.dumps(call.arguments, sort_keys=True)}"
            seen[key] += 1
            if seen[key] > max_repeats:  # stop condition: thrashing
                trace.append(f"stop: {key} repeated {seen[key]} times")
                return RunResult(None, "repetition", step, trace)
            observation = execute(tools, call)  # observe
            trace.append(f"{call.name}({call.arguments}) -> {observation[:80]}")
            messages.append(Message("tool", observation, tool_call_id=call.id))
    return RunResult(None, "max_steps", max_steps, trace)  # stop condition: budget
