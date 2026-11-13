"""STARTER. TODO: a PR body a reviewer can trust: plan, change, before/after test
report, diff stat, cost.

P1 milestone 5: from a resolved run to a pull request (on the local forge only).

The PR body is what a reviewer needs and nothing the agent can't back up: the plan, what
changed and why (the model's one-line summary), the diff stat, the before/after test
report measured by the loop, and the run's cost. Escalated runs open no PR; they produce
an issue comment instead.
"""

from __future__ import annotations

from p1_agent import Outcome
from p1_kit import LocalForge, PullRequest, Sandbox, git


def pr_body(sb: Sandbox, outcome: Outcome, diffstat: str) -> str:
    return f"Fix {sb.issue.title}"  # TODO


def escalation_comment(sb: Sandbox, outcome: Outcome) -> str:
    return (
        f"Agent could not fix #{sb.issue.number}: {outcome.reason}.\n"
        f"Tried {outcome.test_runs} test runs and {outcome.tool_calls} tool calls; "
        "no changes were pushed."
    )


def open_pr(sb: Sandbox, outcome: Outcome, forge: LocalForge) -> PullRequest | None:
    if outcome.status != "resolved":
        return None
    wt = sb.worktree
    git(wt, "add", "--", "src")
    stat = git(wt, "diff", "--cached", "--stat")
    git(wt, "commit", "-qm", f"Fix #{sb.issue.number}: {sb.issue.title}")
    git(wt, "push", "-q", "origin", sb.branch)
    return forge.open_pr(
        head=sb.branch,
        base="main",
        title=f"Fix #{sb.issue.number}: {sb.issue.title}",
        body=pr_body(sb, outcome, stat),
        labels=["agent", "needs-review"],
    )
