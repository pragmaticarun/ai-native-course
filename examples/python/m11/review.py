"""M11 L11.4: review workflow for agent PRs — size limits, provenance, routing and an
AI pre-review that runs before a human looks.

Conventions here are this course's (state them in your CONTRIBUTING/AGENTS.md):
* provenance: the `agent-authored` label, or an `Agent-Session:` trailer in a commit;
* size: added + removed lines, not counting lockfiles and generated files; the limit
  (400 here) is a team choice, not a researched threshold;
* the person who prompted the agent can't be the only approver of its PR.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from rules import glob_match

GENERATED = (
    "**/*.lock",
    "**/pnpm-lock.yaml",
    "**/package-lock.json",
    "**/uv.lock",
    "**/*_pb2.py",
    "**/dist/**",
)


@dataclass
class PR:
    number: int
    title: str
    author: str
    requested_by: str | None
    labels: set[str]
    commits: list[str]
    files: dict[str, tuple[int, int]]  # path -> (added, removed)
    diff: str = ""


def provenance(pr: PR) -> str:
    if "agent-authored" in pr.labels or any(
        re.search(r"^Agent-Session: \S+", c, re.M) for c in pr.commits
    ):
        return "agent"
    return "human"


def size(pr: PR) -> int:
    return sum(
        a + r
        for path, (a, r) in pr.files.items()
        if not any(glob_match(g, path) for g in GENERATED)
    )


@dataclass
class Decision:
    provenance: str
    size: int
    blockers: list[str] = field(default_factory=list)
    reviewers_needed: int = 1
    not_allowed_as_sole_approver: set[str] = field(default_factory=set)
    prereview: list[str] = field(default_factory=list)


def decide(pr: PR, prereview: Callable[[PR], list[str]], limit: int = 400) -> Decision:
    d = Decision(provenance(pr), size(pr))
    if d.size > limit:
        d.blockers.append(f"{d.size} changed lines > {limit}: split into stacked PRs")
    if d.provenance == "agent":
        d.prereview = prereview(pr)  # attached before any human is pinged
        d.blockers += [f"pre-review: {c}" for c in d.prereview if c.startswith("BLOCK")]
        if pr.requested_by:
            d.not_allowed_as_sole_approver.add(pr.requested_by)
        if any(p.startswith(("migrations/", ".github/workflows/")) for p in pr.files):
            d.reviewers_needed = 2
    return d


def mock_prereview(pr: PR) -> list[str]:
    """Stand-in for an AI reviewer (Copilot code review, `claude -p`, `codex review`, ...)."""
    notes = []
    code = [p for p in pr.files if p.startswith("src/")]
    tests = [p for p in pr.files if p.startswith("tests/")]
    if code and not tests:
        notes.append("BLOCK: code changed without tests")
    if re.search(r"^\+.*\b(TODO|FIXME)\b", pr.diff, re.M):
        notes.append("NOTE: new TODO without an issue link")
    if re.search(r"^-\s*assert ", pr.diff, re.M):
        notes.append("BLOCK: removes an assertion")
    return notes
