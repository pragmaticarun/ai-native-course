"""A tiny, provider-agnostic chat-model interface.

The course's own examples talk to models through `ChatModel.complete()`.
`ScriptedModel` is the deterministic mock used by every test and by default
in every example. `get_model()` picks the backend from environment variables:

    COURSE_LLM_PROVIDER = mock | openai | anthropic   (default: mock)
    COURSE_LLM_MODEL    = the provider's model id      (required for live)
    plus that provider's own key variable (OPENAI_API_KEY / ANTHROPIC_API_KEY)

Live adapters are thin and are NOT exercised in CI (no keys in CI).
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Role = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    id: str = "call_0"


@dataclass(frozen=True)
class Message:
    role: Role
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None  # set when role == "tool"


@dataclass(frozen=True)
class AssistantTurn:
    """What a model returns: text, tool calls, or both."""

    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    input_tokens: int = 0
    output_tokens: int = 0

    def as_message(self) -> Message:
        return Message("assistant", self.text, self.tool_calls)


@dataclass(frozen=True)
class ToolSpec:
    """A tool as the model sees it: a name, a description and a JSON Schema."""

    name: str
    description: str
    parameters: dict[str, Any]


class ChatModel(Protocol):
    def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolSpec] = ()
    ) -> AssistantTurn: ...


Script = Sequence[AssistantTurn] | Callable[[Sequence[Message], Sequence[ToolSpec]], AssistantTurn]


@dataclass
class ScriptedModel:
    """Deterministic mock model.

    Give it either a list of turns (returned in order) or a function that looks
    at the conversation and decides what to return. `calls` records every
    request so tests can assert on what the "model" was shown.
    """

    script: Script
    calls: list[list[Message]] = field(default_factory=list)

    def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolSpec] = ()
    ) -> AssistantTurn:
        self.calls.append(list(messages))
        if callable(self.script):
            turn = self.script(messages, tools)
        else:
            index = len(self.calls) - 1
            if index >= len(self.script):
                raise RuntimeError(f"ScriptedModel ran out of turns after {len(self.script)} calls")
            turn = self.script[index]
        prompt_chars = sum(len(m.content) for m in messages)
        out_chars = len(turn.text) + sum(len(json.dumps(c.arguments)) for c in turn.tool_calls)
        # Rough, clearly fake accounting so token-budget examples have numbers to work with.
        return AssistantTurn(
            turn.text, turn.tool_calls, max(1, prompt_chars // 4), max(1, out_chars // 4)
        )


def get_model(default_script: Script | None = None) -> ChatModel:
    """Return the model selected by COURSE_LLM_PROVIDER (mock by default)."""
    provider = os.environ.get("COURSE_LLM_PROVIDER", "mock").strip().lower()
    if provider == "mock":
        return ScriptedModel(default_script or [AssistantTurn(text="Hello from the mock model.")])
    model_id = os.environ.get("COURSE_LLM_MODEL")
    if not model_id:
        raise RuntimeError("Set COURSE_LLM_MODEL to your provider's model id for live mode.")
    if provider == "openai":
        return _OpenAIChat(model_id)
    if provider == "anthropic":
        return _AnthropicChat(model_id)
    raise RuntimeError(f"Unknown COURSE_LLM_PROVIDER={provider!r} (use mock, openai or anthropic)")


# --------------------------------------------------------------------------- live adapters
# These are intentionally minimal and untested in CI. They translate our neutral
# Message/ToolSpec types to each vendor's request format and back.


class _OpenAIChat:
    def __init__(self, model_id: str) -> None:
        from openai import OpenAI  # optional dependency: `uv sync --extra live`

        self._client = OpenAI()
        self._model = model_id

    def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolSpec] = ()
    ) -> AssistantTurn:
        payload: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "tool":
                payload.append(
                    {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content}
                )
            elif m.tool_calls:
                payload.append(
                    {
                        "role": "assistant",
                        "content": m.content or None,
                        "tool_calls": [
                            {
                                "id": c.id,
                                "type": "function",
                                "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                            }
                            for c in m.tool_calls
                        ],
                    }
                )
            else:
                payload.append({"role": m.role, "content": m.content})
        kwargs: dict[str, Any] = {"model": self._model, "messages": payload}
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
        resp = self._client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        calls = tuple(
            ToolCall(c.function.name, json.loads(c.function.arguments or "{}"), c.id)
            for c in (msg.tool_calls or [])
        )
        usage = resp.usage
        return AssistantTurn(
            msg.content or "",
            calls,
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
        )


class _AnthropicChat:
    def __init__(self, model_id: str) -> None:
        from anthropic import Anthropic  # optional dependency: `uv sync --extra live`

        self._client = Anthropic()
        self._model = model_id

    def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolSpec] = ()
    ) -> AssistantTurn:
        system = "\n".join(m.content for m in messages if m.role == "system")
        payload: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "system":
                continue
            if m.role == "tool":
                payload.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.tool_call_id,
                                "content": m.content,
                            }
                        ],
                    }
                )
            elif m.tool_calls:
                blocks: list[dict[str, Any]] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                blocks += [
                    {"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments}
                    for c in m.tool_calls
                ]
                payload.append({"role": "assistant", "content": blocks})
            else:
                payload.append({"role": m.role, "content": m.content})
        kwargs: dict[str, Any] = {"model": self._model, "max_tokens": 1024, "messages": payload}
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.parameters}
                for t in tools
            ]
        resp = self._client.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = tuple(
            ToolCall(b.name, dict(b.input), b.id) for b in resp.content if b.type == "tool_use"
        )
        return AssistantTurn(text, calls, resp.usage.input_tokens, resp.usage.output_tokens)
