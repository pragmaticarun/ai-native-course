"""P1 milestone 4: the agent loop, with a budget and a verified finish.

The loop owns everything the model must not be trusted with: the budget (steps, test
runs, estimated tokens), the tool guardrails (in `Workspace`), and the definition of done.
A model saying "finish" is a claim; the loop re-runs the full suite itself and checks the
diff is non-empty and inside the editable paths before it calls the issue resolved.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from p1_context import estimate_tokens, repo_map
from p1_kit import Issue, Model, Step, ToolCall
from p1_tools import TestReport, Workspace


@dataclass
class Budget:
    max_steps: int = 120
    max_test_runs: int = 60
    max_tokens: int = 150_000


@dataclass
class Outcome:
    status: str  # resolved | escalated | budget
    reason: str = ""
    plan: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    tokens: int = 0
    test_runs: int = 0
    tool_calls: int = 0
    seconds: float = 0.0
    before: TestReport | None = None
    after: TestReport | None = None
    summary: str = ""


def run_agent(issue: Issue, ws: Workspace, model: Model, budget: Budget | None = None) -> Outcome:
    budget = budget or Budget()
    t0 = time.perf_counter()
    rmap = repo_map(ws.root)
    out = Outcome("budget", tokens=estimate_tokens(rmap + issue.title + issue.body))

    def done(status: str, reason: str = "") -> Outcome:
        out.status, out.reason = status, reason
        out.test_runs, out.tool_calls = ws.test_runs, ws.tool_calls
        out.before = ws.reports[0] if ws.reports else None
        out.seconds = round(time.perf_counter() - t0, 2)
        return out

    for _ in range(budget.max_steps):
        call = model.next(issue, rmap, out.steps)
        out.tokens += estimate_tokens(repr(call.args)) + 20  # the model's own output
        if call.name == "plan":
            out.plan = [str(s) for s in call.args.get("steps", [])]
            out.steps.append(Step(call, "plan recorded", True))
            continue
        if call.name == "give_up":
            return done("escalated", str(call.args.get("reason", "")))
        if call.name == "finish":
            verdict = verify(ws)
            if verdict is None:
                out.summary = str(call.args.get("summary", ""))
                out.after = ws.reports[-1]
                return done("resolved")
            out.steps.append(Step(call, f"finish rejected: {verdict}", False))
            continue
        if ws.test_runs >= budget.max_test_runs and call.name == "run_tests":
            return done("budget", f"test-run budget ({budget.max_test_runs}) spent")
        ok, text = ws.call(call)
        out.steps.append(Step(call, text, ok))
        out.tokens += estimate_tokens(text)
        if out.tokens > budget.max_tokens:
            return done("budget", f"token budget ({budget.max_tokens}) spent")
    return done("budget", f"step budget ({budget.max_steps}) spent")


def verify(ws: Workspace) -> str | None:
    """None if the work is really done, else why not."""
    changed = ws.changed_paths()
    if not changed:
        return "no changes"
    outside = [p for p in changed if not any(p.startswith(e) for e in ws.editable)]
    if outside:
        return f"changes outside editable paths: {outside}"
    ws.call(ToolCall("run_tests", {}))
    report = ws.reports[-1]
    if not report.green:
        return f"suite not green: {report.summary()}"
    return None
