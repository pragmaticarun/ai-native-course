"""P1 milestone 6: the 15-seeded-bug benchmark.

Each bug gets a fresh sandbox (clone + seeded bug + worktree + bare origin), one agent
run, and a PR or an escalation. Scored per bug:

* resolved and expected to be fixable → good; `exact` says whether the fix restored the
  original line (a different, test-passing edit is still a fix, but worth a look);
* escalated and expected to need new logic → good (an honest "I can't");
* anything else, or a test file touched, or a PR opened while the suite is red → bad.

Run: `uv run --project python python projects/p1/solution/p1_bench.py`
"""

from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from p1_agent import Budget, run_agent  # noqa: E402
from p1_kit import BUGS, FIXTURE, LocalForge, make_sandbox  # noqa: E402
from p1_pr import open_pr  # noqa: E402
from p1_repairer import ScriptedRepairModel  # noqa: E402
from p1_tools import Workspace  # noqa: E402


@dataclass
class Row:
    bug: str
    expected: str
    status: str
    correct: bool
    exact: bool
    pr: int | None
    test_runs: int
    tool_calls: int
    tokens: int
    seconds: float
    tests_touched: bool


def run_one(tmp: Path, bug: dict, number: int, budget: Budget | None = None) -> Row:
    sb = make_sandbox(tmp, bug, number)
    ws = Workspace(sb.worktree)
    outcome = run_agent(sb.issue, ws, ScriptedRepairModel(), budget)
    touched = any(p.startswith("tests/") for p in ws.changed_paths())
    pr = open_pr(sb, outcome, LocalForge(sb.origin))
    exact = (sb.worktree / bug["file"]).read_text() == (FIXTURE / bug["file"]).read_text()
    correct = outcome.status == ("resolved" if bug["expected"] == "resolve" else "escalated")
    return Row(bug["id"], bug["expected"], outcome.status, correct and not touched,
               exact, pr.number if pr else None, outcome.test_runs, outcome.tool_calls,
               outcome.tokens, outcome.seconds, touched)  # fmt: skip


def run_bench(bugs: list[dict] | None = None) -> list[Row]:
    rows = []
    for i, bug in enumerate(bugs or BUGS, 1):
        with tempfile.TemporaryDirectory() as tmp:
            rows.append(run_one(Path(tmp), bug, i))
    return rows


def summary(rows: list[Row]) -> dict[str, float]:
    fixable = [r for r in rows if r.expected == "resolve"]
    return {
        "bugs": len(rows),
        "resolved": sum(r.status == "resolved" for r in rows),
        "resolve_rate_fixable": round(
            sum(r.status == "resolved" for r in fixable) / len(fixable), 3
        ),
        "correct_outcome_rate": round(sum(r.correct for r in rows) / len(rows), 3),
        "exact_fixes": sum(r.exact and r.status == "resolved" for r in rows),
        "tests_touched": sum(r.tests_touched for r in rows),
        "mean_test_runs": round(sum(r.test_runs for r in rows) / len(rows), 1),
        "mean_tokens": round(sum(r.tokens for r in rows) / len(rows)),
        "total_seconds": round(sum(r.seconds for r in rows), 1),
    }  # fmt: skip


def table(rows: list[Row]) -> str:
    head = "| bug | expected | outcome | PR | exact | test runs | tool calls | ~tokens |\n|---|---|---|---|---|---|---|---|"  # noqa: E501
    body = "\n".join(
        f"| {r.bug} | {r.expected} | {r.status} | {('#' + str(r.pr)) if r.pr else '—'} | "
        f"{'yes' if r.exact else 'no'} | {r.test_runs} | {r.tool_calls} | {r.tokens} |"
        for r in rows
    )
    return f"{head}\n{body}"


if __name__ == "__main__":
    rs = run_bench()
    print(table(rs))
    print(summary(rs))
