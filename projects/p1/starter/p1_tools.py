"""STARTER. TODO: the guardrails. Today any path works, tests are writable, run_tests
passes options straight to pytest with your full environment, and output is never
truncated.

P1 milestone 2: the agent's tools, with guardrails in the tools themselves.

The model can list, read and search the repo, edit files under `src/` only, and run the
test suite. Guardrails, enforced here rather than in the prompt:

* paths stay inside the worktree: no absolute paths, no `..`, no symlink escapes;
* `.git` is invisible, and tests are read-only (the tests are the oracle; an agent that
  edits them to go green has not fixed anything);
* `run_tests` takes only test node ids (no pytest options), runs with a scrubbed
  environment, a timeout, and a `sitecustomize` that makes any socket use fail. That is a
  guard against accidents, not a security sandbox: real isolation needs a container or
  network namespace (untested in this course);
* every result is truncated, and every call is counted for the budget.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from p1_kit import ToolCall, git

NO_NETWORK = """import socket


def _blocked(*args, **kwargs):
    raise PermissionError("network access is disabled in the P1 sandbox")


socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked
socket.getaddrinfo = _blocked
"""
TOOLS = ("list_files", "read_file", "search", "replace", "edit_line", "run_tests", "diff")


class GuardError(Exception):
    """A refused tool call. The message goes back to the model."""


@dataclass
class TestReport:
    passed: int
    failed: int
    errors: int
    failed_ids: list[str]
    output: str

    @property
    def green(self) -> bool:
        return self.failed == 0 and self.errors == 0 and self.passed > 0

    def summary(self) -> str:
        return f"{self.passed} passed, {self.failed} failed, {self.errors} errors"


def parse_pytest(output: str) -> TestReport:
    summary = next(
        (ln for ln in reversed(output.splitlines()) if re.search(r"\d+ (passed|failed|error)", ln)
         and re.search(r" in [\d.]+s", ln)),
        "",
    )  # fmt: skip

    def count(word: str) -> int:
        m = re.search(rf"(\d+) {word}", summary)
        return int(m.group(1)) if m else 0

    failed_ids = re.findall(r"^(?:FAILED|ERROR) (\S+)", output, re.M)
    return TestReport(count("passed"), count("failed"), count("error"), failed_ids, output)


@dataclass
class Workspace:
    root: Path
    editable: tuple[str, ...] = ("src/",)
    max_output: int = 3000
    test_timeout: float = 60
    tool_calls: int = 0
    test_runs: int = 0
    refused: list[str] = field(default_factory=list)
    reports: list[TestReport] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.root = Path(self.root).resolve()
        self._guard_dir = Path(tempfile.mkdtemp(prefix="p1-guard-"))
        (self._guard_dir / "sitecustomize.py").write_text(NO_NETWORK)

    # ---------------------------------------------------------------- path guard
    def resolve(self, rel: str, write: bool = False) -> Path:
        # TODO: refuse absolute paths, "..", .git, symlink escapes; writes only under editable.
        return self.root / rel

    def _clip(self, text: str) -> str:
        return text  # TODO: truncate to max_output and say how much was cut

    # ---------------------------------------------------------------- tools
    def list_files(self) -> str:
        files = [
            p.relative_to(self.root).as_posix()
            for p in sorted(self.root.rglob("*"))
            if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
        ]
        return "\n".join(files)

    def read_file(self, path: str, start: int = 1, end: int | None = None) -> str:
        lines = self.resolve(path).read_text().splitlines()
        end = len(lines) if end is None else min(end, len(lines))
        return "\n".join(f"{i:4d}| {lines[i - 1]}" for i in range(max(start, 1), end + 1))

    def search(self, pattern: str) -> str:
        try:
            rx = re.compile(pattern)
        except re.error as e:
            raise GuardError(f"bad regex: {e}") from e
        hits = []
        for p in sorted(self.root.rglob("*.py")):
            if ".git" in p.parts:
                continue
            for i, line in enumerate(p.read_text().splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{p.relative_to(self.root).as_posix()}:{i}: {line.strip()}")
        return "\n".join(hits[:50]) or "no matches"

    def replace(self, path: str, old: str, new: str) -> str:
        f = self.resolve(path, write=True)
        src = f.read_text()
        n = src.count(old)
        if n != 1:
            raise GuardError(f"`old` must match exactly once in {path} (matched {n})")
        f.write_text(src.replace(old, new))
        return f"edited {path}"

    def edit_line(self, path: str, line: int, expected: str, new: str) -> str:
        f = self.resolve(path, write=True)
        lines = f.read_text().splitlines(keepends=True)
        if not 1 <= line <= len(lines) or lines[line - 1].rstrip("\n") != expected:
            raise GuardError(f"line {line} of {path} is not what you expected (stale view?)")
        lines[line - 1] = new + "\n"
        f.write_text("".join(lines))
        return f"edited {path}:{line}"

    def run_tests(self, select: list[str] | None = None) -> str:
        select = select or []
        # TODO: accept only test node ids under tests/ (no pytest options)
        # TODO: a scrubbed environment with the no-network sitecustomize on PYTHONPATH
        env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
        cmd = [sys.executable, "-m", "pytest", "-q", "-rfE", "--tb=short", "-p", "no:cacheprovider"]
        try:
            out = subprocess.run(
                [*cmd, *select], cwd=self.root, env=env, capture_output=True, text=True,
                timeout=self.test_timeout,
            )  # fmt: skip
        except subprocess.TimeoutExpired as e:
            raise GuardError(f"tests timed out after {self.test_timeout}s") from e
        self.test_runs += 1
        report = parse_pytest(out.stdout + out.stderr)
        self.reports.append(report)
        return self._clip(report.output)

    def diff(self) -> str:
        return git(self.root, "diff", "--", *self.editable) or "no changes"

    def changed_paths(self) -> list[str]:
        return git(self.root, "diff", "--name-only").split()

    # ---------------------------------------------------------------- dispatch
    def call(self, tc: ToolCall) -> tuple[bool, str]:
        self.tool_calls += 1
        if tc.name not in TOOLS:
            return False, f"unknown tool {tc.name!r}; tools: {', '.join(TOOLS)}"
        try:
            text = getattr(self, tc.name)(**tc.args)
        except GuardError as e:
            self.refused.append(f"{tc.name}: {e}")
            return False, f"refused: {e}"
        except (TypeError, FileNotFoundError, IsADirectoryError, UnicodeDecodeError) as e:
            return False, f"error: {e}"
        return True, self._clip(text)
