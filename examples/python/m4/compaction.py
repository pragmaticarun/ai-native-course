"""L4.2: short-term memory. Compact a long conversation.

Strategy:
* keep the last `keep_last` turns verbatim (the model needs recent detail);
* replace everything older with a summary written by a model;
* copy "pinned" lines (decisions, constraints, user facts) into the summary
  word for word, because summaries lose exactly those details.

The summariser is any `ChatModel`; tests use a scripted one.
"""

from __future__ import annotations

from collections.abc import Sequence

from context_budget import approx_tokens

from aincourse import AssistantTurn, ChatModel, Message, ScriptedModel

PIN_PREFIXES = ("DECISION:", "CONSTRAINT:", "FACT:")


def pinned_lines(messages: Sequence[Message]) -> list[str]:
    return [
        line.strip()
        for m in messages
        for line in m.content.splitlines()
        if line.strip().startswith(PIN_PREFIXES)
    ]


def compact(
    messages: Sequence[Message], summariser: ChatModel, keep_last: int = 4
) -> list[Message]:
    """Return [system?, summary, *last turns]. The system prompt is never summarised."""
    system = [m for m in messages if m.role == "system"]
    rest = [m for m in messages if m.role != "system"]
    if len(rest) <= keep_last:
        return list(messages)
    old, recent = rest[:-keep_last], rest[-keep_last:]
    transcript = "\n".join(f"{m.role}: {m.content}" for m in old)
    turn = summariser.complete(
        [
            Message("system", "Summarise this conversation in under 80 words."),
            Message("user", transcript),
        ]
    )
    pins = pinned_lines(old)
    summary = "Summary of earlier conversation: " + turn.text.strip()
    if pins:
        summary += "\nPinned (verbatim):\n" + "\n".join(pins)
    return [*system, Message("user", summary), *recent]


def tokens(messages: Sequence[Message]) -> int:
    return sum(approx_tokens(m.content) for m in messages)


def demo_conversation() -> list[Message]:
    msgs = [Message("system", "You help plan a media pipeline.")]
    for i in range(12):
        msgs.append(Message("user", f"Turn {i}: " + "background chatter " * 30))
        msgs.append(Message("assistant", f"Reply {i}: " + "long explanation " * 30))
    msgs.insert(3, Message("user", "DECISION: output is 48 kHz stereo AAC."))
    msgs.insert(6, Message("user", "CONSTRAINT: must run on a Galaxy A73 CPU."))
    return msgs


if __name__ == "__main__":
    convo = demo_conversation()
    summariser = ScriptedModel([AssistantTurn(text="We discussed the pipeline design.")])
    short = compact(convo, summariser)
    print(f"{tokens(convo)} -> {tokens(short)} tokens")
    print(short[1].content)
