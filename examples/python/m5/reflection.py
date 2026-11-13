"""L5.2: reflection. A deterministic verifier beats a model critic when you have one.

`refine()` drafts, checks, and revises up to `max_rounds`. The check can be:
* a deterministic verifier (tests, a schema, a linter): cheap and trustworthy;
* a critic model: costs a call per round and can approve wrong answers.
The demo counts model calls and tokens for both so you can see the trade-off.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aincourse import AssistantTurn, ChatModel, Message, ScriptedModel

Verifier = Callable[[str], str | None]  # returns an error message, or None if OK


@dataclass
class Refined:
    answer: str
    ok: bool
    rounds: int
    model_calls: int
    tokens: int


def refine(writer: ChatModel, task: str, verify: Verifier, max_rounds: int = 3) -> Refined:
    messages = [Message("user", task)]
    calls = tokens = 0
    answer = ""
    for rnd in range(1, max_rounds + 1):
        turn = writer.complete(messages)
        calls += 1
        tokens += turn.input_tokens + turn.output_tokens
        answer = turn.text
        problem = verify(answer)
        if problem is None:
            return Refined(answer, True, rnd, calls, tokens)
        messages += [turn.as_message(), Message("user", f"Problem: {problem}. Revise.")]
    return Refined(answer, False, max_rounds, calls, tokens)


def critic_verifier(critic: ChatModel, counter: list[int]) -> Verifier:
    def verify(answer: str) -> str | None:
        counter[0] += 1
        verdict = critic.complete(
            [Message("user", f"Is this correct? Reply OK or the problem.\n{answer}")]
        ).text
        return None if verdict.strip() == "OK" else verdict

    return verify


def ffmpeg_cmd_verifier(answer: str) -> str | None:
    """Deterministic check for a 'trim to 10 s without re-encoding' ffmpeg command."""
    parts = answer.split()
    if not parts or parts[0] != "ffmpeg":
        return "must start with ffmpeg"
    if "-t" not in parts or parts[parts.index("-t") + 1] != "10":
        return "duration must be -t 10"
    if "-c" not in parts or parts[parts.index("-c") + 1] != "copy":
        return "use -c copy to avoid re-encoding"
    return None


DRAFTS = [
    AssistantTurn(text="ffmpeg -i in.mp4 -t 10 out.mp4"),
    AssistantTurn(text="ffmpeg -i in.mp4 -t 10 -c copy out.mp4"),
]

if __name__ == "__main__":
    det = refine(
        ScriptedModel(DRAFTS), "Trim in.mp4 to 10 s without re-encoding.", ffmpeg_cmd_verifier
    )
    print("deterministic verifier:", det)
    count = [0]
    lenient = ScriptedModel([AssistantTurn(text="OK")])  # a critic that approves the wrong draft
    crit = refine(ScriptedModel(DRAFTS), "Trim...", critic_verifier(lenient, count))
    print("lenient critic:", crit, "critic calls:", count[0])
