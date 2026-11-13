"""P1 kit (provided, not part of the exercise): the benchmark repo, seeded bugs, git
sandboxes and a local "forge" that stands in for GitHub.

Nothing here touches the network or a real GitHub repo. "Opening a PR" means pushing a
branch to a local bare repository (`origin`) and recording the PR in a JSON file.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixture_repo"
BUGS = json.loads((HERE / "bugs.json").read_text())


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout


@dataclass
class Issue:
    number: int
    title: str
    body: str
    bug_id: str = ""


@dataclass
class Sandbox:
    """A clone of the benchmark repo with one seeded bug on `main`, pushed to a local
    bare `origin`, plus a worktree on a fresh branch for the agent."""

    root: Path
    origin: Path
    main: Path
    worktree: Path
    branch: str
    issue: Issue


def make_sandbox(tmp: Path, bug: dict[str, Any] | None = None, number: int = 1) -> Sandbox:
    origin = tmp / "origin.git"
    main = tmp / "textkit"
    shutil.copytree(FIXTURE, main, ignore=shutil.ignore_patterns("__pycache__"))
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    git(main, "init", "-q", "-b", "main")
    git(main, "config", "user.email", "maintainer@example.com")
    git(main, "config", "user.name", "maintainer")
    git(main, "add", ".")
    git(main, "commit", "-qm", "textkit: initial")
    if bug is not None:
        f = main / bug["file"]
        src = f.read_text()
        assert src.count(bug["find"]) == 1, f"seed for {bug['id']} must match exactly once"
        f.write_text(src.replace(bug["find"], bug["replace"]))
        git(main, "commit", "-qam", f"refactor ({bug['id']})")
    git(main, "remote", "add", "origin", str(origin))
    git(main, "push", "-q", "origin", "main")
    issue = Issue(number, bug["title"], bug["body"], bug["id"]) if bug else Issue(number, "", "")
    branch = f"agent/issue-{number}"
    wt = tmp / f"wt-{number}"
    git(main, "worktree", "add", "-q", "-b", branch, str(wt))
    git(wt, "config", "user.email", "agent@example.com")
    git(wt, "config", "user.name", "mini-swe")
    return Sandbox(tmp, origin, main, wt, branch, issue)


@dataclass
class PullRequest:
    number: int
    head: str
    base: str
    title: str
    body: str
    labels: list[str] = field(default_factory=list)


class LocalForge:
    """The smallest stand-in for GitHub: PRs are JSON records, and a PR can only be
    opened for a branch that exists on the bare origin."""

    def __init__(self, origin: Path) -> None:
        self.origin = origin
        self.db = origin / "pulls.json"

    def pulls(self) -> list[PullRequest]:
        if not self.db.exists():
            return []
        return [PullRequest(**p) for p in json.loads(self.db.read_text())]

    def open_pr(
        self, head: str, base: str, title: str, body: str, labels: list[str]
    ) -> PullRequest:
        branches = git(self.origin, "branch", "--format=%(refname:short)").split()
        if head not in branches:
            raise ValueError(f"branch {head} is not on origin")
        prs = self.pulls()
        pr = PullRequest(len(prs) + 1, head, base, title, body, labels)
        self.db.write_text(json.dumps([asdict(p) for p in [*prs, pr]], indent=1))
        return pr


@dataclass
class ToolCall:
    """What a model asks for. `name` is a tool, or `plan`, `finish`, `give_up`."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class Step:
    call: ToolCall
    result: str
    ok: bool


class Model(Protocol):
    """A coding model: sees the issue, a repo map and the steps so far; returns the next
    call. Real backends (an LLM through Pydantic AI, the Claude Agent SDK, the AI SDK)
    would sit behind this; the course's tests use a scripted model."""

    def next(self, issue: Issue, repo_map: str, history: list[Step]) -> ToolCall: ...
