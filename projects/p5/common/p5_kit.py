"""P5 kit (provided): the legacy team repo, ten seeded tasks, hidden acceptance tests and a
mock coding agent, so you can measure the repo before and after your changes.

The agent is a deterministic stand-in (as in M10), not a model:
* it runs the verify command the repo documents in AGENTS.md (`Verify: `...``); with none,
  it guesses `python -m pytest -q`, as a newcomer reading this README would;
* for each task it tries its candidate patches in order and keeps the first one that passes
  that command (or its first candidate if none passes), then opens a PR.
Success is judged by hidden acceptance tests (`acceptance/`), which the agent never sees.
"Rework" = the agent's own check passed but the acceptance tests fail: a PR a reviewer would
merge and someone would have to fix later.

The numbers are a property of this mock and these fixtures. They show how to measure; they
are not evidence about any real agent or team.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LEGACY = HERE / "legacy_repo"
ACCEPT = HERE / "acceptance"
TASKS: list[dict[str, Any]] = json.loads((HERE / "tasks.json").read_text())
GUESS = [sys.executable, "-m", "pytest", "-q"]
IGNORE = shutil.ignore_patterns("target", "node_modules", "__pycache__", ".pytest_cache")


def have_tools() -> dict[str, bool]:
    node = shutil.which("node")
    ok_node = False
    if node:
        v = subprocess.run([node, "--version"], capture_output=True, text=True).stdout
        major, minor = (int(x) for x in v.strip().lstrip("v").split(".")[:2])
        ok_node = (major, minor) >= (22, 6)  # --experimental-strip-types
    return {"node": ok_node, "cargo": shutil.which("cargo") is not None}


def make_repo(dest: Path, overlay: Path | None = None) -> Path:
    """Copy the legacy repo to `dest`, then your overlay (the repo changes) on top."""
    # copy without metadata: fresh mtimes, so cargo never trusts a stale build
    shutil.copytree(LEGACY, dest, ignore=IGNORE, copy_function=shutil.copy)
    if overlay is not None:
        shutil.copytree(overlay, dest, dirs_exist_ok=True, ignore=IGNORE, copy_function=shutil.copy)
    for sh in dest.rglob("*.sh"):
        sh.chmod(0o755)
    return dest


def documented_verify(repo: Path) -> list[str] | None:
    agents = repo / "AGENTS.md"
    if agents.exists():
        m = re.search(r"^Verify: `([^`]+)`", agents.read_text(), re.M)
        if m:
            return m.group(1).split()
    return None


def _env(target: Path) -> dict[str, str]:
    return {
        **os.environ,
        "PYTHON": sys.executable,
        "CARGO_TARGET_DIR": str(target),
        "CARGO_NET_OFFLINE": "true",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "NODE_NO_WARNINGS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",  # patches within one second must not reuse stale .pyc
    }


def run(cmd: list[str], repo: Path, target: Path) -> tuple[bool, float, str]:
    t = time.perf_counter()
    p = subprocess.run(cmd, cwd=repo, env=_env(target), capture_output=True, text=True, timeout=600)
    return p.returncode == 0, time.perf_counter() - t, (p.stdout + p.stderr)[-2000:]


def accepted(task: dict[str, Any], repo: Path, target: Path) -> bool:
    """The hidden ground truth for one task's language."""
    lang = task["lang"]
    if lang == "py":
        env = {**_env(target), "PYTHONPATH": str(repo / "py")}
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            str(ACCEPT / "test_accept.py"),
        ]
        return subprocess.run(cmd, cwd=ACCEPT, env=env, capture_output=True).returncode == 0
    if lang == "ts":
        dst = repo / "web" / "test" / "__accept.test.ts"
        dst.parent.mkdir(exist_ok=True)
        shutil.copy(ACCEPT / "accept.test.ts", dst)
        try:
            cmd = ["node", "--experimental-strip-types", "--no-warnings", "--test", str(dst)]
            return run(cmd, repo, target)[0]
        finally:
            dst.unlink()
    dst = repo / "rust" / "clipcore" / "tests" / "__accept.rs"
    shutil.copy(ACCEPT / "accept.rs", dst)
    try:
        cmd = ["cargo", "test", "--quiet", "--offline", "--test", "__accept"]
        return run(cmd, repo / "rust" / "clipcore", target)[0]
    finally:
        dst.unlink()


def _patch(repo: Path, task: dict[str, Any], old: str, new: str) -> None:
    f = repo / task["file"]
    text = f.read_text()
    assert old in text, f"{task['id']}: snippet not found in {task['file']}"
    f.write_text(text.replace(old, new, 1))


@dataclass
class TaskResult:
    task: str
    lang: str
    solved: bool
    self_check_passed: bool
    verify_runs: int
    changed_lines: int
    pr_body: str

    @property
    def rework(self) -> bool:
        return self.self_check_passed and not self.solved


@dataclass
class BenchResult:
    label: str
    verify_cmd: list[str]
    tasks: list[TaskResult] = field(default_factory=list)
    verify_seconds: float = 0.0  # one clean verify run on the unmodified repo
    clean_verify_passes: bool = False

    @property
    def success_rate(self) -> float:
        return sum(t.solved for t in self.tasks) / len(self.tasks)

    @property
    def rework_rate(self) -> float:
        return sum(t.rework for t in self.tasks) / len(self.tasks)

    @property
    def verify_runs(self) -> int:
        return sum(t.verify_runs for t in self.tasks)


def bench(workdir: Path, label: str, overlay: Path | None = None) -> BenchResult:
    repo = make_repo(workdir / label, overlay)
    target = workdir / f"target-{label}"  # one build dir per repo copy
    verify = documented_verify(repo) or GUESS
    res = BenchResult(label, verify)
    res.clean_verify_passes, res.verify_seconds, _ = run(verify, repo, target)
    for task in TASKS:
        _patch(repo, task, task["reference"], task["bug"])
        current, passed, runs, chosen = task["bug"], False, 0, task["candidates"][0]
        for cand in task["candidates"]:
            _patch(repo, task, current, cand)
            current = cand
            runs += 1
            if run(verify, repo, target)[0]:
                chosen, passed = cand, True
                break
        _patch(repo, task, current, chosen)
        solved = accepted(task, repo, target)
        body = (
            f"Fixes: {task['issue']}\n\nAgent-Session: mock-{task['id']}\n"
            f"Checked with: `{' '.join(verify)}` -> {'pass' if passed else 'FAIL'}"
        )
        res.tasks.append(TaskResult(task["id"], task["lang"], solved, passed, runs, 2, body))
        _patch(repo, task, chosen, task["reference"])  # reset for the next task
    return res
