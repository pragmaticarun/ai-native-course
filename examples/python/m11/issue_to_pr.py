"""M11 L11.5 worked example: issue → agent → tests → PR, with a budget and a kill switch.

Runs against a local sandbox repo (no network, no GitHub API): "opening the PR" means
committing to a branch and writing the PR body. The agent is scripted. The same
pipeline shape is what the GitHub Actions template in workflows/ wires to a live
coding agent behind a manual trigger (that path is untested in this course).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from sandbox import git, pytest_run


@dataclass
class Issue:
    number: int
    title: str
    body: str
    labels: set[str]


@dataclass
class Budget:
    max_steps: int = 8
    max_usd: float = 1.00


@dataclass
class Edit:
    path: str
    content: str
    usd: float = 0.05


@dataclass
class RunTests:
    usd: float = 0.01


@dataclass
class Done:
    summary: str
    usd: float = 0.0


Action = Edit | RunTests | Done


@dataclass
class Outcome:
    status: str
    steps: int = 0
    usd: float = 0.0
    branch: str | None = None
    pr_body: str = ""
    log: list[str] = field(default_factory=list)


def killed(repo: Path, env: dict[str, str]) -> bool:
    return env.get("AGENT_PIPELINE_DISABLED") == "1" or (repo / ".agent-stop").exists()


def run_pipeline(
    repo: Path, issue: Issue, agent: Iterator[Action], budget: Budget, env: dict[str, str]
) -> Outcome:
    if "agent:ok" not in issue.labels:
        return Outcome("skipped: issue not labelled agent:ok")
    out = Outcome("running")
    branch = f"agent/issue-{issue.number}"
    git(repo, "switch", "-q", "-c", branch)
    for action in agent:
        if killed(repo, env):
            out.status = "stopped: kill switch"
            break
        if out.steps + 1 > budget.max_steps or out.usd + action.usd > budget.max_usd:
            out.status = "stopped: budget"
            break
        out.steps += 1
        out.usd = round(out.usd + action.usd, 4)
        if isinstance(action, Edit):
            (repo / action.path).write_text(action.content)
            out.log.append(f"edit {action.path}")
        elif isinstance(action, RunTests):
            passed = pytest_run(repo).returncode == 0
            out.log.append(f"tests {'pass' if passed else 'fail'}")
        else:
            final = pytest_run(repo)  # the pipeline re-checks; it never trusts the agent's word
            if final.returncode != 0:
                out.status = "failed: tests"
                break
            git(repo, "add", "-A")
            git(
                repo,
                "commit",
                "-qm",
                f"{issue.title}\n\nCloses #{issue.number}\nAgent-Session: mock-{issue.number}",
            )
            out.status, out.branch = "ready", branch
            out.pr_body = pr_body(issue, action.summary, out, final.stdout.strip().splitlines()[-1])
            break
    else:
        out.status = "failed: agent stopped without finishing"
    if out.status != "ready":
        git(repo, "reset", "-q", "--hard")
        git(repo, "switch", "-q", "main")
        git(repo, "branch", "-q", "-D", branch)
    return out


def pr_body(issue: Issue, summary: str, out: Outcome, test_line: str) -> str:
    return (
        f"Closes #{issue.number}\n\n{summary}\n\n"
        f"- Provenance: agent-authored (label `agent-authored`); a human must review before merge.\n"  # noqa: E501
        f"- Tests: `{test_line}`\n"
        f"- Agent steps: {out.steps}, estimated cost ${out.usd:.2f}\n"
        f"- Log: {', '.join(out.log)}\n"
    )


FIX = '''def trim(duration_s: float, start_s: float, end_s: float) -> float:
    """Length of the clip between start and end, clamped to the media."""
    if end_s < start_s:
        raise ValueError(f"end {end_s} is before start {start_s}")
    return min(end_s, duration_s) - start_s
'''


def scripted_agent() -> Iterator[Action]:
    yield RunTests()
    yield Edit("src/clip.py", FIX)
    yield RunTests()
    yield Done("Clamp `trim` to the media duration and reject reversed ranges.")
