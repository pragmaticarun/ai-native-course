"""P1 evals: guardrails, context, the loop, the PR, and the 15-bug benchmark.

Run against the solution (must pass) and the starter (must fail):
PROJECT_VARIANT=starter|solution pytest projects/p1/evals
"""

import socket
import tempfile
from pathlib import Path

import pytest
from p1_agent import Budget, run_agent
from p1_context import called_names, locate, repo_map
from p1_kit import BUGS, Issue, LocalForge, Step, ToolCall, git, make_sandbox
from p1_pr import open_pr
from p1_repairer import ScriptedRepairModel, mutants
from p1_tools import Workspace, parse_pytest

BUG = {b["id"]: b for b in BUGS}


@pytest.fixture
def sb(tmp_path):
    return make_sandbox(tmp_path, BUG["P1-03-clamp"], 7)


# ------------------------------------------------------------------ M1 context
def test_repo_map_fits_budget_and_names_functions(sb):
    m = repo_map(sb.worktree, budget_chars=1600)
    assert len(m) <= 1650 and "def clamp(x, lo, hi): Limit x" in m
    small = repo_map(sb.worktree, budget_chars=200)
    assert len(small) <= 260 and "more lines; use search" in small


def test_called_names_and_locate():
    test_src = "from m import f\n\ndef test_a():\n    assert f(g(1)) == 2\n"
    assert called_names(test_src, "test_a") == ["f", "g"]
    src = 'def f(x):\n    """Doc."""\n    y = x\n    return y\n'
    assert locate(src, "f") == (3, 4)


# ------------------------------------------------------------------ M2 tools + guardrails
@pytest.mark.parametrize(
    "call",
    [
        ToolCall("read_file", {"path": "/etc/passwd"}),
        ToolCall("read_file", {"path": "../origin.git/config"}),
        ToolCall("read_file", {"path": ".git/config"}),
        ToolCall("replace", {"path": "tests/test_stats.py", "old": "assert", "new": "pass  #"}),
        ToolCall("replace", {"path": "pytest.ini", "old": "src", "new": "x"}),
        ToolCall("run_tests", {"select": ["--co"]}),
        ToolCall("run_tests", {"select": ["src/textkit/stats.py"]}),
    ],
)
def test_guardrails_refuse(sb, call):
    ws = Workspace(sb.worktree)
    ok, text = ws.call(call)
    assert not ok and text.startswith("refused"), text
    assert ws.refused


def test_symlink_escape_refused(sb):
    (sb.worktree / "src" / "leak").symlink_to(sb.root)
    ok, text = Workspace(sb.worktree).call(ToolCall("read_file", {"path": "src/leak/pulls.json"}))
    assert not ok and "escapes" in text


def test_unknown_tool_and_bad_args(sb):
    ws = Workspace(sb.worktree)
    ok, text = ws.call(ToolCall("shell", {"cmd": "curl x"}))
    assert not ok and text.startswith("unknown tool 'shell'")
    ok, text = ws.call(ToolCall("read_file", {"nope": 1}))
    assert not ok and text.startswith("error")


def test_edit_line_rejects_stale_view(sb):
    ws = Workspace(sb.worktree)
    ok, text = ws.call(ToolCall("edit_line", {"path": "src/textkit/stats.py", "line": 22,
                                              "expected": "    return 1", "new": "x"}))  # fmt: skip
    assert not ok and "stale" in text


def test_tests_run_without_network(sb):
    (sb.worktree / "tests" / "test_net.py").write_text(
        "import socket\n\ndef test_net():\n    socket.create_connection(('example.com', 80))\n"
    )
    ws = Workspace(sb.worktree)
    ws.call(ToolCall("run_tests", {"select": ["tests/test_net.py"]}))
    assert "network access is disabled" in ws.reports[-1].output
    assert socket.create_connection is not None  # the host process is untouched


def test_output_truncated_and_counted(sb):
    ws = Workspace(sb.worktree, max_output=100)
    ok, text = ws.call(ToolCall("read_file", {"path": "src/textkit/strings.py"}))
    assert ok and "[truncated" in text and len(text) < 160
    assert ws.tool_calls == 1


def test_parse_pytest_ignores_trailing_noise():
    out = ".F\nFAILED tests/t.py::test_x - assert 1 == 2\n1 failed, 1 passed in 0.02s\nWarning: x\n"
    r = parse_pytest(out)
    assert (r.passed, r.failed, r.failed_ids) == (1, 1, ["tests/t.py::test_x"])


# ------------------------------------------------------------------ M3 repair model
def test_mutants_are_single_site_and_skip_arrows():
    ms = mutants("    return a < b and c -> d")
    assert "    return a <= b and c -> d" in ms and "    return a < b or c -> d" in ms
    assert all("->" in m for m in ms)
    assert mutants('    """a < b"""') == []


# ------------------------------------------------------------------ M4 loop + budget
class Runaway:
    """A model that never stops calling tools."""

    def next(self, issue, repo_map, history):
        return ToolCall("run_tests", {})


class Cheater:
    """Tries to make the suite green by editing tests, then claims success."""

    def __init__(self):
        self.n = 0

    def next(self, issue, repo_map, history):
        self.n += 1
        if self.n == 1:
            old = "    assert clamp(5, 0, 10) == 5\n"
            return ToolCall("replace", {"path": "tests/test_stats.py", "old": old, "new": ""})
        return ToolCall("finish", {"summary": "all good"}) if self.n < 4 else ToolCall("give_up")


def test_budget_stops_a_runaway(sb):
    ws = Workspace(sb.worktree)
    out = run_agent(sb.issue, ws, Runaway(), Budget(max_test_runs=3))
    assert out.status == "budget" and ws.test_runs == 3


def test_finish_is_verified_not_trusted(sb):
    out = run_agent(sb.issue, Workspace(sb.worktree), Cheater(), Budget())
    assert out.status == "escalated"
    rejected = [s.result for s in out.steps if s.call.name == "finish"]
    assert rejected and all(r.startswith("finish rejected") for r in rejected)
    assert git(sb.worktree, "diff", "--name-only") == ""


# ------------------------------------------------------------------ M5 end to end + PR
def test_issue_to_pr_on_local_forge(sb):
    ws = Workspace(sb.worktree)
    out = run_agent(sb.issue, ws, ScriptedRepairModel())
    assert (
        out.status == "resolved"
        and out.before
        and not out.before.green
        and out.after is not None
        and out.after.green
    )
    forge = LocalForge(sb.origin)
    pr = open_pr(sb, out, forge)
    assert pr is not None and forge.pulls()[0].head == "agent/issue-7"
    assert "Fixes #7" in pr.body
    assert "| before (on `main`) | 19 passed, 1 failed, 0 errors |" in pr.body
    assert "max(lo, min(x, hi))" in pr.body and "Tests were not modified" in pr.body
    assert git(sb.origin, "diff", "--name-only", "main", "agent/issue-7").split() == [
        "src/textkit/stats.py"
    ]  # noqa: E501


def test_escalation_opens_no_pr(tmp_path):
    sb = make_sandbox(tmp_path, BUG["P1-12-dedupe"], 3)
    out = run_agent(sb.issue, Workspace(sb.worktree), ScriptedRepairModel())
    assert out.status == "escalated" and "needs a human" in out.reason
    assert open_pr(sb, out, LocalForge(sb.origin)) is None
    assert "agent/issue-3" not in git(sb.origin, "branch")


def test_forge_refuses_unpushed_branch(sb):
    with pytest.raises(ValueError):
        LocalForge(sb.origin).open_pr("nope", "main", "t", "b", [])


# ------------------------------------------------------------------ M6 benchmark
def test_benchmark_15_seeded_bugs():
    from p1_bench import run_bench, summary

    rows = run_bench()
    s = summary(rows)
    assert s["bugs"] == 15 and len({b["id"] for b in BUGS}) == 15
    assert s["correct_outcome_rate"] == 1.0, [(r.bug, r.status) for r in rows if not r.correct]
    assert s["resolved"] == 13 and s["tests_touched"] == 0
    assert s["exact_fixes"] >= 12  # mean() is fixed by an equivalent, non-identical edit
    assert all(r.pr is not None for r in rows if r.status == "resolved")


def test_seeds_apply_cleanly():
    for b in BUGS:
        with tempfile.TemporaryDirectory() as t:
            sb = make_sandbox(Path(t), b, 1)
            ws = Workspace(sb.worktree)
            ws.call(ToolCall("run_tests", {}))
            assert not ws.reports[-1].green, b["id"]


def test_history_type_is_shared():
    assert Step(ToolCall("plan"), "x", True).ok and Issue(1, "t", "b").number == 1
