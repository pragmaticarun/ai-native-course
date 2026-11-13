"""P1 milestone 1: context engineering on a repo.

The model can't read the whole repo every turn, so it gets a compact *repo map* (files,
function signatures and their first docstring line) within a character budget, and finds
the rest with tools. `called_names` and `locate` are the small static analyses the
scripted model uses after reading files through those tools.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Rough token count (4 characters per token). Good enough for a budget, not billing."""
    return max(1, len(text) // 4)


def repo_map(root: Path, budget_chars: int = 1600, src: str = "src") -> str:
    lines: list[str] = []
    for f in sorted((root / src).rglob("*.py")):
        tree = ast.parse(f.read_text())
        defs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        if not defs:
            continue
        lines.append(f.relative_to(root).as_posix())
        for d in defs:
            doc = (ast.get_docstring(d) or "").splitlines()
            args = ", ".join(a.arg for a in d.args.args)
            lines.append(f"  def {d.name}({args}): {doc[0] if doc else ''}".rstrip())
    out: list[str] = []
    used = 0
    for i, line in enumerate(lines):
        if used + len(line) + 1 > budget_chars:
            out.append(f"… ({len(lines) - i} more lines; use search)")
            break
        out.append(line)
        used += len(line) + 1
    return "\n".join(out)


def strip_numbers(numbered: str) -> str:
    """Undo read_file's `   12| ` prefixes."""
    return "\n".join(re.sub(r"^\s*\d+\| ?", "", line) for line in numbered.splitlines())


def called_names(test_source: str, test_name: str) -> list[str]:
    """Functions a test calls, in order of first use."""
    tree = ast.parse(test_source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == test_name:
            names: list[str] = []
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    if sub.func.id not in names:
                        names.append(sub.func.id)
            return names
    return []


def locate(source: str, func: str) -> tuple[int, int] | None:
    """1-based (first body line, last line) of a top-level function."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == func:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                start = node.body[1].lineno if len(node.body) > 1 else first.lineno
            else:
                start = first.lineno
            return start, node.end_lineno or start
    return None
