"""M6 worked example: an eval suite for the M3 explorer agent.

30 generated cases over a fixture repo, three question types:
  * "Where is `X` defined?"       -> answer must name the right file
  * "Which files mention `Y`?"    -> answer must list exactly the right files
  * "What does `f` return?"       -> answer must quote the return expression
Every case also has trajectory checks: grep first, at most 4 tool calls, and
never `list_dir` on a question grep can answer.

The mock agent has a deliberate blind spot (it only greps `def`, so it can't
find classes). The suite catches it: that is what a regression suite is for.
Costs use ILLUSTRATIVE prices (not any provider's) applied to the mock model's
rough token counts.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "m3"))

from explorer_agent import make_tools  # noqa: E402
from graders import Case, SuiteResult, at_most_calls, calls_first, contains, never_calls, run_suite  # noqa: E402
from scratch_loop import run_agent  # noqa: E402

from aincourse import AssistantTurn, ChatModel, Message, ScriptedModel, ToolCall, ToolSpec  # noqa: E402

PRICE_PER_MTOK = {"input": 1.00, "output": 4.00}  # illustrative USD, not a real price list

FUNCS = [f"handler_{i}" for i in range(10)]
CLASSES = ["Muxer", "Demuxer", "Resampler"]


def build_fixture_repo(root: Path) -> None:
    (root / "src").mkdir(parents=True, exist_ok=True)
    for i, name in enumerate(FUNCS):
        (root / "src" / f"mod{i}.py").write_text(
            f"import logging\n\n\ndef {name}(x):\n"
            f"    logging.info('{name}')\n    return x * {i + 2}\n"
        )
    for name in CLASSES:
        (root / "src" / f"{name.lower()}.py").write_text(
            f"class {name}:\n    def run(self):\n        return '{name}'\n"
        )
    (root / "README.md").write_text("Uses logging everywhere.\n")


def cases() -> list[Case]:
    traj = [calls_first("grep"), at_most_calls(4), never_calls("list_dir")]
    out: list[Case] = []
    for i, f in enumerate(FUNCS):
        out.append(
            Case(
                f"def-{f}",
                f"Where is `{f}` defined?",
                [contains(f"src/mod{i}.py"), *traj],
                ("where",),
            )
        )
        out.append(
            Case(
                f"ret-{f}",
                f"What does `{f}` return?",
                [contains(f"x * {i + 2}"), *traj],
                ("returns",),
            )
        )
    for c in CLASSES:
        out.append(
            Case(
                f"class-{c}",
                f"Where is `{c}` defined?",
                [contains(f"src/{c.lower()}.py"), *traj],
                ("where", "class"),
            )
        )
    for i in range(7):
        f = FUNCS[i]
        out.append(
            Case(
                f"mention-{f}",
                f"Which files mention `{f}`?",
                [contains(f"src/mod{i}.py"), *traj],
                ("mentions",),
            )
        )
    return out


def policy(messages: Sequence[Message], tools: Sequence[ToolSpec]) -> AssistantTurn:
    q = next(m.content for m in messages if m.role == "user")
    obs = [m.content for m in messages if m.role == "tool"]
    sym = re.search(r"`([^`]+)`", q).group(1)  # type: ignore[union-attr]
    if q.startswith("Which files mention"):
        if not obs:
            return AssistantTurn(tool_calls=(ToolCall("grep", {"pattern": sym, "path": "."}),))
        files = sorted({line.split(":", 1)[0] for line in obs[0].splitlines() if ":" in line})
        return AssistantTurn(text="Files: " + ", ".join(files))
    if not obs:  # blind spot: only functions are searched for
        return AssistantTurn(tool_calls=(ToolCall("grep", {"pattern": f"def {sym}", "path": "."}),))
    if obs[0] == "no matches":
        return AssistantTurn(text=f"I could not find `{sym}`.")
    path = obs[0].split(":", 1)[0]
    if q.startswith("Where"):
        return AssistantTurn(text=f"`{sym}` is defined in {path}.")
    if len(obs) == 1:
        return AssistantTurn(tool_calls=(ToolCall("read_file", {"path": path}, "c2"),))
    ret = next(line.strip() for line in obs[1].splitlines() if line.strip().startswith("return"))
    return AssistantTurn(text=f"`{sym}` does `{ret}`.")


@dataclass
class Metered:
    """Wraps a model and adds up tokens, so the suite can report cost."""

    inner: ChatModel
    input_tokens: int = 0
    output_tokens: int = 0

    def complete(self, messages, tools=()):
        turn = self.inner.complete(messages, tools)
        self.input_tokens += turn.input_tokens
        self.output_tokens += turn.output_tokens
        return turn

    @property
    def cost_usd(self) -> float:
        return (
            self.input_tokens * PRICE_PER_MTOK["input"]
            + self.output_tokens * PRICE_PER_MTOK["output"]
        ) / 1e6


def run(root: Path) -> tuple[SuiteResult, Metered]:
    meter = Metered(ScriptedModel(policy))

    def agent(question: str) -> tuple[str, list[str]]:
        r = run_agent(meter, make_tools(root), question, max_steps=6)
        return r.answer or "", [t.split("(", 1)[0] for t in r.trace]

    return run_suite(cases(), agent), meter


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        build_fixture_repo(Path(d))
        res, meter = run(Path(d))
        print(f"pass {res.passed}/{res.total} ({res.rate:.0%})")
        for cid, probs in res.failures.items():
            print(f"  FAIL {cid}: {probs}")
        print(
            f"tokens in/out {meter.input_tokens}/{meter.output_tokens}, "
            f"illustrative cost ${meter.cost_usd:.6f}"
        )
