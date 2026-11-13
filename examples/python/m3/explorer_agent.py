"""L3 worked example: a read-only file-system "explorer" agent with a step budget.

Tools are read-only and sandboxed to one root directory (path traversal is
rejected). The default "model" is scripted so this runs offline.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from scratch_loop import RunResult, Tool, run_agent

from aincourse import AssistantTurn, ChatModel, Message, ScriptedModel, ToolCall, ToolSpec


def _obj(**props: str) -> dict:
    return {
        "type": "object",
        "properties": {k: {"type": v} for k, v in props.items()},
        "required": list(props),
        "additionalProperties": False,
    }


def make_tools(root: Path) -> dict[str, Tool]:
    root = root.resolve()

    def safe(rel: str) -> Path:
        p = (root / rel).resolve()
        if not p.is_relative_to(root):
            raise PermissionError(f"{rel!r} is outside the sandbox")
        return p

    def list_dir(path: str = ".") -> str:
        return "\n".join(
            sorted(f"{c.name}/" if c.is_dir() else c.name for c in safe(path).iterdir())
        )

    def read_file(path: str, max_chars: int = 2000) -> str:
        return safe(path).read_text(errors="replace")[:max_chars]

    def text_files(base: Path) -> list[Path]:
        """Visible text files only: skip dot-dirs (.git, .venv) and binaries."""
        out = []
        for f in sorted(base.rglob("*")):
            rel = f.relative_to(root).parts
            if f.is_file() and not any(p.startswith(".") for p in rel):
                if b"\0" not in f.read_bytes()[:1024]:
                    out.append(f)
        return out

    def grep(pattern: str, path: str = ".") -> str:
        hits = [
            f"{f.relative_to(root)}:{i}: {line.strip()}"
            for f in text_files(safe(path))
            for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1)
            if pattern in line
        ]
        return "\n".join(hits[:50]) or "no matches"

    return {
        "list_dir": Tool(
            ToolSpec("list_dir", "List a directory (read-only).", _obj(path="string")), list_dir
        ),
        "read_file": Tool(
            ToolSpec("read_file", "Read a text file (read-only, truncated).", _obj(path="string")),
            read_file,
        ),
        "grep": Tool(
            ToolSpec(
                "grep",
                "Find lines containing a literal string.",
                _obj(pattern="string", path="string"),
            ),
            grep,
        ),
    }


def scripted_explorer(messages: Sequence[Message], tools: Sequence[ToolSpec]) -> AssistantTurn:
    """Fake model: grep for the entry point, read it, answer from what it read."""
    observations = [m.content for m in messages if m.role == "tool"]
    if not observations:
        return AssistantTurn(
            tool_calls=(ToolCall("grep", {"pattern": "def main", "path": "."}, "c1"),)
        )
    if observations[0] == "no matches":
        return AssistantTurn(text="I found no `def main` in this tree.")
    if len(observations) == 1:
        first_hit = observations[0].split(":", 1)[0]
        return AssistantTurn(tool_calls=(ToolCall("read_file", {"path": first_hit}, "c2"),))
    path = observations[0].split(":", 1)[0]
    return AssistantTurn(text=f"The entry point is main() in {path}.")


def explore(
    root: Path, question: str, model: ChatModel | None = None, max_steps: int = 6
) -> RunResult:
    return run_agent(
        model or ScriptedModel(scripted_explorer),
        make_tools(root),
        question,
        system="You explore a codebase with read-only tools.",
        max_steps=max_steps,
    )


if __name__ == "__main__":
    result = explore(Path(sys.argv[1] if len(sys.argv) > 1 else "."), "Where is the entry point?")
    print("\n".join(result.trace))
    print(result.stop_reason, "->", result.answer)
