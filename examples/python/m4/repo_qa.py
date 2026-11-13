"""M4 worked example: a repo-QA agent that stays under a 20k-token budget.

The codebase is generated (50 modules x 1,000 lines = 50,000 lines), so the test
is reproducible. The agent never reads whole files: it greps, then reads small
line ranges, and every tool result is truncated. A budget guard checks the
prompt size before every model call and compacts old tool results if needed.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from context_budget import approx_tokens, truncate_to_tokens

from aincourse import AssistantTurn, ChatModel, Message, ScriptedModel, ToolCall, ToolSpec

BUDGET = 20_000
RESULT_CAP = 1_500  # tokens per tool result


def generate_codebase(root: Path, modules: int = 50, lines_per_module: int = 1000) -> int:
    total = 0
    for m in range(modules):
        out = [f'"""Module {m}: synthetic code for the repo-QA example."""', ""]
        n = 0
        while len(out) < lines_per_module - 12:
            out += [f"def handler_{m}_{n}(x):", f"    return x * {m} + {n}", ""]
            n += 1
        if m == 37:
            out += [
                "",
                "def parse_config(path):",
                "    # the one the questions ask about",
                "    return open(path).read()",
            ]
        while len(out) < lines_per_module:
            out.append("# padding")
        out = out[:lines_per_module]
        (root / f"mod_{m:02d}.py").write_text("\n".join(out) + "\n")
        total += len(out)
    return total


def make_tools(root: Path) -> tuple[list[ToolSpec], dict]:
    def grep(pattern: str) -> str:
        hits = []
        for f in sorted(root.glob("*.py")):
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if pattern in line:
                    hits.append(f"{f.name}:{i}: {line.strip()}")
        return truncate_to_tokens("\n".join(hits) or "no matches", RESULT_CAP)

    def read_range(path: str, start: int, end: int) -> str:
        p = (root / path).resolve()
        if p.parent != root.resolve():
            return "error: path outside repo"
        end = min(end, start + 60)  # never more than 60 lines at once
        lines = p.read_text().splitlines()[start - 1 : end]
        body = "\n".join(f"{start + i}: {line}" for i, line in enumerate(lines))
        return truncate_to_tokens(body, RESULT_CAP)

    obj = {"type": "object"}
    specs = [
        ToolSpec(
            "grep",
            "Find lines containing a literal string.",
            {**obj, "properties": {"pattern": {"type": "string"}}},
        ),
        ToolSpec(
            "read_range",
            "Read at most 60 lines.",
            {
                **obj,
                "properties": {
                    "path": {"type": "string"},
                    "start": {"type": "integer"},
                    "end": {"type": "integer"},
                },
            },
        ),
    ]
    return specs, {"grep": grep, "read_range": read_range}


def scripted_qa(messages: Sequence[Message], tools: Sequence[ToolSpec]) -> AssistantTurn:
    """Mock policy: grep for the symbol, read around the hit, answer with a citation."""
    question = next(m.content for m in messages if m.role == "user")
    observations = [m.content for m in messages if m.role == "tool"]
    symbol = re.search(r"`([^`]+)`", question)
    if symbol is None:
        return AssistantTurn(text="Please name the symbol in backticks.")
    if not observations:
        return AssistantTurn(tool_calls=(ToolCall("grep", {"pattern": f"def {symbol.group(1)}("}),))
    if len(observations) == 1:
        first = observations[0].splitlines()[0]
        if first == "no matches":
            return AssistantTurn(text=f"`{symbol.group(1)}` is not defined in this repo.")
        path, line, _ = first.split(":", 2)
        return AssistantTurn(
            tool_calls=(
                ToolCall(
                    "read_range", {"path": path, "start": int(line), "end": int(line) + 5}, "c2"
                ),
            )
        )
    path_line = observations[0].split(":", 2)
    return AssistantTurn(text=f"`{symbol.group(1)}` is defined at {path_line[0]}:{path_line[1]}.")


@dataclass
class QAResult:
    answer: str
    max_prompt_tokens: int
    calls: int
    prompt_sizes: list[int] = field(default_factory=list)


def prompt_tokens(messages: Sequence[Message], specs: Sequence[ToolSpec]) -> int:
    return sum(approx_tokens(m.content) for m in messages) + approx_tokens(
        json.dumps([s.parameters for s in specs])
    )


def ask(root: Path, question: str, model: ChatModel | None = None, max_steps: int = 6) -> QAResult:
    specs, fns = make_tools(root)
    model = model or ScriptedModel(scripted_qa)
    messages = [
        Message("system", "Answer questions about the repo. Cite path:line."),
        Message("user", question),
    ]
    sizes: list[int] = []
    for _ in range(max_steps):
        size = prompt_tokens(messages, specs)
        if size > BUDGET:  # guard: drop the bodies of the oldest tool results
            for i, m in enumerate(messages):
                if m.role == "tool" and size > BUDGET:
                    messages[i] = Message(
                        "tool", "[elided to save context]", tool_call_id=m.tool_call_id
                    )
                    size = prompt_tokens(messages, specs)
        if size > BUDGET:
            raise RuntimeError("cannot fit the prompt in the budget")
        sizes.append(size)
        turn = model.complete(messages, specs)
        if not turn.tool_calls:
            return QAResult(turn.text, max(sizes), len(sizes), sizes)
        messages.append(turn.as_message())
        for call in turn.tool_calls:
            messages.append(
                Message("tool", str(fns[call.name](**call.arguments)), tool_call_id=call.id)
            )
    return QAResult("step budget exhausted", max(sizes), len(sizes), sizes)


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        lines = generate_codebase(root)
        r = ask(root, "Where is `parse_config` defined?")
        print(
            f"{lines} lines indexed; answer: {r.answer}; max prompt ~{r.max_prompt_tokens} tokens"
        )
