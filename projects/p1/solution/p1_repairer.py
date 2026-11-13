"""P1 milestone 3: a scripted coding "model" (no LLM).

It drives the same tools an LLM would, one call at a time, and sees only tool output:

1. plan from the issue and the repo map;
2. reproduce: run the whole suite, collect failing test ids;
3. localise: read each failing test, find the library functions it calls, find and read
   their definitions;
4. repair by *mutation search*: try small, classic edits on each line of the suspect
   function (flip a comparison, swap +/-, and/or, min/max, True/False, drop a stray
   ±1), keep an edit only if the failing tests pass and then the whole suite passes,
   and revert it otherwise;
5. give up honestly (escalate to a human) when no single edit works.

This is classic search-based program repair, chosen because it is deterministic and
testable. It fixes exactly the bugs a one-token edit can fix; anything that needs new
logic is escalated, which is the behaviour we want from any agent when it is stuck.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Generator

from p1_context import called_names, locate, strip_numbers
from p1_kit import Issue, Step, ToolCall

# (pattern, replacement): regexes so that `<` doesn't match inside `<=` or `->`.
MUTATIONS: list[tuple[str, str]] = [
    (r"<=", "<"), (r"(?<![<-])<(?!=)", "<="), (r">=", ">"), (r"(?<![->])>(?!=)", ">="),
    (r"==", "!="), (r"!=", "=="), (r" \+ (?!1\b)", " - "), (r" - (?!1\b)", " + "),
    (r" - 1\b", ""), (r" \+ 1\b", ""), (r" - 1\b", " + 1"), (r" \+ 1\b", " - 1"),
    (r"\band\b", "or"), (r"\bor\b", "and"), (r"\bmin\(", "max("), (r"\bmax\(", "min("),
    (r"\bTrue\b", "False"), (r"\bFalse\b", "True"),
]  # fmt: skip


def mutants(line: str) -> list[str]:
    """Every single-site mutation of a line, in MUTATIONS order, skipping duplicates.
    Docstrings and comments are left alone."""
    code = line.split("#", 1)[0]
    if code.strip().startswith(('"""', "'''", '"', "'")):
        return []
    out: list[str] = []
    for pat, rep in MUTATIONS:
        for m in re.finditer(pat, code):
            new = line[: m.start()] + m.expand(rep) + line[m.end() :]
            if new != line and new not in out:
                out.append(new)
    return out


def failed_ids(output: str) -> list[str]:
    return re.findall(r"^(?:FAILED|ERROR) (\S+?)(?: - |$)", output, re.M)


def parses(source: str) -> bool:
    try:
        ast.parse(source)
    except SyntaxError:
        return False
    return True


class ScriptedRepairModel:
    def __init__(self) -> None:
        self._gen: Generator[ToolCall, str] | None = None

    def next(self, issue: Issue, repo_map: str, history: list[Step]) -> ToolCall:
        if self._gen is None:
            self._gen = self._script(issue, repo_map)
            return next(self._gen)
        try:
            return self._gen.send(history[-1].result)
        except StopIteration:
            return ToolCall("give_up", {"reason": "script ended"})

    def _script(self, issue: Issue, repo_map: str) -> Generator[ToolCall, str]:
        known = re.findall(r"def (\w+)\(", repo_map)
        mentioned = [f for f in known if re.search(rf"\b{f}\b", issue.title + " " + issue.body)]
        yield ToolCall("plan", {"steps": [
            f"Reproduce issue #{issue.number} with the test suite",
            f"Localise: start from {', '.join(mentioned) or 'the failing tests'}",
            "Try minimal edits; keep one only if the failing tests and then the full suite pass",
            "Open a PR with the diff and a before/after test report, or escalate",
        ]})  # fmt: skip

        out = yield ToolCall("run_tests", {})
        failing = failed_ids(out)
        if not failing:
            yield ToolCall("give_up", {"reason": "could not reproduce: the suite is green"})
            return

        suspects: list[str] = [f for f in mentioned]
        for tid in failing:
            path, _, name = tid.partition("::")
            src = strip_numbers((yield ToolCall("read_file", {"path": path})))
            for fn in called_names(src, name):
                if fn in known and fn not in suspects:
                    suspects.append(fn)

        for fn in suspects:
            hit = yield ToolCall("search", {"pattern": rf"^def {fn}\("})
            m = re.match(r"(\S+?):\d+:", hit)
            if not m:
                continue
            path = m.group(1)
            source = strip_numbers((yield ToolCall("read_file", {"path": path})))
            span = locate(source, fn)
            if span is None:
                continue
            lines = source.splitlines()
            for lineno in range(span[0], span[1] + 1):
                old = lines[lineno - 1]
                for new in mutants(old):
                    trial = lines.copy()
                    trial[lineno - 1] = new
                    if not parses("\n".join(trial)):
                        continue  # don't spend a test run on a syntax error
                    yield ToolCall("edit_line", {"path": path, "line": lineno, "expected": old, "new": new})  # fmt: skip # noqa: E501
                    out = yield ToolCall("run_tests", {"select": failing})
                    if not failed_ids(out) and " passed" in out:
                        out = yield ToolCall("run_tests", {})
                        if not failed_ids(out):
                            yield ToolCall("finish", {
                                "summary": f"`{fn}` in {path}, line {lineno}: "
                                f"`{old.strip()}` → `{new.strip()}`",
                            })  # fmt: skip
                            return
                    yield ToolCall("edit_line", {"path": path, "line": lineno, "expected": new, "new": old})  # fmt: skip # noqa: E501
        yield ToolCall("give_up", {
            "reason": f"no single-line edit to {', '.join(suspects) or 'any suspect'} makes "
            f"{len(failing)} failing test(s) pass; needs a human or a stronger model",
        })  # fmt: skip
