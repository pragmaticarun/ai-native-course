from pathlib import Path

import dora
import issue_to_pr as itp
import review
import tdd_gate
import workflow_lint
import worktrees
from sandbox import git, make_sandbox

HERE = Path(__file__).parent

# --- L11.2: TDD gate ------------------------------------------------------------------


def test_honest_fix_passes_the_gate(tmp_path):
    repo = make_sandbox(tmp_path)
    approval = tdd_gate.approve_tests(repo)
    assert approval.was_red and approval.collected == 3
    (repo / "src" / "clip.py").write_text(itp.FIX)
    assert tdd_gate.gate(repo, approval) == []


def test_tampering_is_caught(tmp_path):
    repo = make_sandbox(tmp_path)
    approval = tdd_gate.approve_tests(repo)
    t = repo / "tests" / "test_clip.py"
    t.write_text(
        t.read_text().replace("assert trim(60, 50, 90) == 10", "assert trim(60, 50, 90) == 40")
    )
    problems = tdd_gate.gate(repo, approval)
    assert "modified approved test tests/test_clip.py" in problems and "tests fail" in problems


def test_skip_in_conftest_is_caught(tmp_path):
    repo = make_sandbox(tmp_path)
    approval = tdd_gate.approve_tests(repo)
    (repo / "tests" / "conftest.py").write_text(
        "import pytest\n\n\ndef pytest_collection_modifyitems(items):\n"
        "    for i in items:\n        i.add_marker(pytest.mark.skip(reason='flaky'))\n"
    )
    assert tdd_gate.gate(repo, approval) == [
        "adds a skip/xfail",
        "touches conftest.py (it can change how tests run)",
    ]


# --- L11.3: worktrees -----------------------------------------------------------------


def rename(src: str) -> str:
    """Written against the original file: it also 'fixes' the return line, differently."""
    return src.replace("def trim", "def trim_clip").replace(
        "return end_s - start_s", "return max(0.0, end_s - start_s)"
    )


EDITS = {
    "probe": {"src/probe.py": lambda _: "def probe():\n    return 'probe'\n"},
    "docs": {"README.md": lambda _: "# clip-tools\n"},
    "clamp": {"src/clip.py": lambda _: itp.FIX},
    "rename": {"src/clip.py": rename},
}


def test_planned_batches_avoid_conflicts(tmp_path):
    repo = make_sandbox(tmp_path)
    files = {name: set(e) for name, e in EDITS.items()}
    batches = worktrees.plan_batches(files)
    assert batches == [["probe", "docs", "clamp"], ["rename"]]
    assert worktrees.run_parallel(repo, batches, EDITS) == []
    merged = (repo / "src" / "clip.py").read_text()
    assert (
        "def trim_clip" in merged and "min(end_s, duration_s)" in merged
    )  # rename ran on top of clamp
    assert git(repo, "worktree", "list").count("\n") == 1  # all agent worktrees cleaned up


def test_naive_parallel_run_conflicts(tmp_path):
    repo = make_sandbox(tmp_path)
    assert worktrees.run_parallel(repo, [list(EDITS)], EDITS) == ["agent/rename"]


# --- L11.4: review --------------------------------------------------------------------


def pr(**kw):
    base = dict(
        number=7,
        title="t",
        author="bot",
        requested_by="asha",
        labels={"agent-authored"},
        commits=["x"],
        files={},
        diff="",
    )
    return review.PR(**{**base, **kw})


def test_agent_pr_policy():
    small = pr(files={"src/clip.py": (6, 1), "tests/test_clip.py": (10, 0), "uv.lock": (900, 300)})
    d = review.decide(small, review.mock_prereview)
    assert (d.provenance, d.size, d.blockers, d.reviewers_needed) == ("agent", 17, [], 1)
    assert d.not_allowed_as_sole_approver == {"asha"}
    big = pr(
        files={"src/a.py": (380, 40), ".github/workflows/ci.yml": (3, 0)},
        diff="-    assert x == 1\n+# TODO later\n",
    )
    d = review.decide(big, review.mock_prereview)
    assert d.blockers == [
        "423 changed lines > 400: split into stacked PRs",
        "pre-review: BLOCK: code changed without tests",
        "pre-review: BLOCK: removes an assertion",
    ]
    assert d.reviewers_needed == 2 and "NOTE: new TODO without an issue link" in d.prereview


def test_provenance_from_trailer():
    assert review.provenance(pr(labels=set(), commits=["Fix\n\nAgent-Session: abc123"])) == "agent"
    assert review.provenance(pr(labels=set(), commits=["Fix"])) == "human"


# --- L11.5: issue -> PR ---------------------------------------------------------------

ISSUE = itp.Issue(
    12, "Clamp trim to the media duration", "trim(60, 50, 90) returns 40", {"bug", "agent:ok"}
)


def test_issue_to_pr_happy_path(tmp_path):
    repo = make_sandbox(tmp_path)
    out = itp.run_pipeline(repo, ISSUE, itp.scripted_agent(), itp.Budget(), {})
    assert (out.status, out.steps, out.usd, out.branch) == ("ready", 4, 0.07, "agent/issue-12")
    assert out.log == ["tests fail", "edit src/clip.py", "tests pass"]
    assert "Closes #12" in out.pr_body and "3 passed" in out.pr_body
    assert "Agent-Session: mock-12" in git(repo, "log", "-1", "--format=%B")


def test_unlabelled_budget_and_kill_switch(tmp_path):
    repo = make_sandbox(tmp_path)
    unlabelled = itp.Issue(13, "x", "y", {"bug"})
    assert (
        itp.run_pipeline(repo, unlabelled, itp.scripted_agent(), itp.Budget(), {}).status
        == "skipped: issue not labelled agent:ok"
    )
    assert (
        itp.run_pipeline(repo, ISSUE, itp.scripted_agent(), itp.Budget(max_usd=0.05), {}).status
        == "stopped: budget"
    )
    out = itp.run_pipeline(
        repo, ISSUE, itp.scripted_agent(), itp.Budget(), {"AGENT_PIPELINE_DISABLED": "1"}
    )
    assert out.status == "stopped: kill switch"
    assert (
        git(repo, "branch", "--show-current").strip() == "main"
        and git(repo, "status", "--porcelain") == ""
    )


def test_agent_claiming_done_on_red_tests_is_refused(tmp_path):
    repo = make_sandbox(tmp_path)

    def liar():
        yield itp.Edit("src/clip.py", itp.FIX.replace("min(end_s, duration_s)", "end_s"))
        yield itp.Done("All fixed!")

    assert itp.run_pipeline(repo, ISSUE, liar(), itp.Budget(), {}).status == "failed: tests"


def test_workflow_template_guardrails():
    text = (HERE / "workflows" / "agent-issue-to-pr.yml").read_text()
    assert workflow_lint.lint_workflow(text) == []
    risky = text.replace(
        "    permissions:\n      contents: read\n      issues: read\n",
        "    permissions:\n      contents: write\n",
        1,
    )
    risky = risky.replace("persist-credentials: false", "persist-credentials: true").replace(
        "--draft ", ""
    )
    assert workflow_lint.lint_workflow(risky) == [
        "agent: holds a secret and has write permissions",
        "agent: checkout persists the token next to the agent",
        "open-pr: PRs must be drafts labelled agent-authored",
    ]


# --- L11.6: measuring -----------------------------------------------------------------


def test_dora_before_after_on_a_fictional_team():
    b_deps, b_prs = dora.fictional_team(
        1, weeks=12, per_week=3, fail_p=0.1, rework_p=0.05, review_h=4
    )
    a_deps, a_prs = dora.fictional_team(
        2, weeks=12, per_week=6, fail_p=0.25, rework_p=0.15, review_h=9
    )
    before, after = dora.metrics(b_deps, b_prs, 12), dora.metrics(a_deps, a_prs, 12)
    assert set(before) == {
        "deployment_frequency_per_week",
        "change_lead_time_h",
        "failed_deployment_recovery_time_h",
        "change_fail_rate",
        "deployment_rework_rate",
        "review_latency_h",
    }
    assert (before["deployment_frequency_per_week"], after["deployment_frequency_per_week"]) == (
        3.0,
        6.0,
    )
    notes = dora.compare(before, after, len(b_deps), len(a_deps))
    assert notes == [
        "amplifier warning: throughput up, instability up",
        "review is the new bottleneck: latency up more than 50%",
    ]
    assert (
        dora.compare(before, after, 8, 40)[0]
        == "too few deployments to compare (need 20 per window)"
    )
