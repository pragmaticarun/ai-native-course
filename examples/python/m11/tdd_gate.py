"""M11 L11.2: TDD with agents — humans approve the tests, the agent makes them pass,
and a gate checks the agent didn't move the goalposts.

Approval records, for the approved test files: their hashes, how many tests pytest
collects, and that the suite was red (failing) at approval time. The gate then refuses
a change that edits or deletes an approved test, adds a skip/xfail anywhere, touches
`conftest.py`, collects fewer tests, or doesn't go green. The rules are this course's;
mature setups also run mutation testing on the result.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from sandbox import git, pytest_run

SKIP = re.compile(r"pytest\.mark\.(skip|xfail)|pytest\.(skip|xfail)\(|unittest\.skip|@skip\b")


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _collected(repo: Path) -> int:
    out = pytest_run(repo, "--collect-only", "-q").stdout
    m = re.search(r"(\d+) tests? collected", out)
    if m:
        return int(m.group(1))
    return sum(int(n) for n in re.findall(r"^\S+\.py: (\d+)$", out, re.M))  # quieter output format


@dataclass(frozen=True)
class Approval:
    base: str
    hashes: dict[str, str]
    collected: int
    was_red: bool


def approve_tests(repo: Path) -> Approval:
    files = sorted(p.relative_to(repo).as_posix() for p in (repo / "tests").rglob("test_*.py"))
    return Approval(
        base=git(repo, "rev-parse", "HEAD").strip(),
        hashes={f: _hash(repo / f) for f in files},
        collected=_collected(repo),
        was_red=pytest_run(repo).returncode != 0,
    )


def gate(repo: Path, approval: Approval) -> list[str]:
    problems = []
    if not approval.was_red:
        problems.append("tests were already green when approved: they don't specify the change")
    for f, h in approval.hashes.items():
        if not (repo / f).exists():
            problems.append(f"deleted approved test {f}")
        elif _hash(repo / f) != h:
            problems.append(f"modified approved test {f}")
    git(repo, "add", "--intent-to-add", ".")  # so new, untracked files show up in the diff
    diff = git(repo, "diff", approval.base, "--unified=0")
    added = [ln[1:] for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    if any(SKIP.search(ln) for ln in added):
        problems.append("adds a skip/xfail")
    if "conftest.py" in git(repo, "diff", approval.base, "--name-only"):
        problems.append("touches conftest.py (it can change how tests run)")
    if _collected(repo) < approval.collected:
        problems.append("fewer tests collected than were approved")
    if pytest_run(repo).returncode != 0:
        problems.append("tests fail")
    return problems
