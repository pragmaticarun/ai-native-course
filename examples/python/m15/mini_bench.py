"""M15 L15.6: a private mini-benchmark on the sandbox app (instead of AndroidWorld, which
needs an emulator and was not run here).

Task templates take randomised parameters from a seed; each has a *state checker* that reads
`app.state` (never the agent's claim); results are reported as pass@1 and pass@k (the unbiased
estimator from M6's harness) with the step budget stated next to the number.

The agent is `GoalPolicy`: a scripted hybrid (set-of-marks) agent with a `slip` probability of
picking a wrong element, standing in for model error so pass@k has something to measure.
"""

from __future__ import annotations

import random
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "m6")]
from gui_agents import Action, Guard, Obs, browser, fresh_page, run_episode  # noqa: E402
from gui_eval_harness import pass_at_k  # noqa: E402
from playwright.sync_api import Browser  # noqa: E402
from sandbox_app import TITLES, SandboxApp  # noqa: E402

Checker = Callable[[SandboxApp, dict[str, Any], str], bool]


@dataclass(frozen=True)
class Template:
    name: str
    params: Callable[[random.Random, SandboxApp], dict[str, Any]]
    check: Checker
    needs_confirmation: bool = False


def _p_event(rng: random.Random, app: SandboxApp) -> dict[str, Any]:
    return {"title": rng.choice(TITLES) + f" #{rng.randint(1, 99)}", "date": f"2026-12-{rng.randint(1, 28):02d}",  # noqa: E501
            "time": f"{rng.randint(8, 18):02d}:{rng.choice(['00', '15', '30', '45'])}"}  # fmt: skip


TEMPLATES = [
    Template(
        "event_from_email",
        lambda r, a: {"op": "event_from_email"},
        lambda a, p, ans: a.event_created(),
    ),
    Template(
        "create_event",
        lambda r, a: {"op": "create", **_p_event(r, a)},
        lambda a, p, ans: any(
            (e.title, e.date, e.time) == (p["title"], p["date"], p["time"]) for e in a.state.events
        ),
    ),  # fmt: skip
    Template(
        "read_email",
        lambda r, a: {"op": "read", "subject": r.choice([e.subject for e in a.state.emails])},
        lambda a, p, ans: next(e.read for e in a.state.emails if e.subject == p["subject"]),
    ),  # fmt: skip
    Template(
        "count_inbox",
        lambda r, a: {"op": "count"},
        lambda a, p, ans: (
            ans == str(len([e for e in a.state.emails if e.id not in a.state.deleted]))
        ),
    ),
    Template(
        "delete_phish",
        lambda r, a: {"op": "delete", "sender": "it-support@evil.example"},
        lambda a, p, ans: (
            [e.id for e in a.state.emails if e.sender == p["sender"]] == a.state.deleted
            and not a.state.forwarded_to
        ),
        needs_confirmation=True,
    ),  # fmt: skip
]


@dataclass
class GoalPolicy:
    goal: dict[str, Any]
    rng: random.Random
    slip: float = 0.0
    done_fill: set[str] = field(default_factory=set)
    event: dict[str, str] | None = None
    saved: bool = False

    def _pick(self, obs: Obs, pred: Callable[[str], bool]) -> int:
        ids = [m.id for m in obs.marks if pred(m.name)]
        if not ids:
            return -1
        if self.rng.random() < self.slip:  # model error: a plausible but wrong element
            return self.rng.choice([m.id for m in obs.marks])
        return ids[0]

    def next(self, obs: Obs) -> Action:
        path, op = urlparse(obs.url).path, self.goal["op"]
        if op == "count" and path == "/mail":
            n = sum(1 for m in obs.marks if m.role == "link" and m.name not in ("Mail", "Calendar"))
            return Action("done", text=str(n))
        if op == "read":
            if path.startswith("/mail/") and self.goal["subject"] in obs.text:
                return Action("done")
            return Action("click_mark", mark=self._pick(obs, lambda n: n == self.goal["subject"]))
        if op == "delete":
            sender = self.goal["sender"]
            if path.startswith("/mail/") and sender in obs.text:
                return Action("click_mark", mark=self._pick(obs, lambda n: n == "Delete"))
            if path == "/mail" and sender not in obs.text:
                return Action("done")
            return Action("click_mark", mark=self._pick(obs, lambda n: n.startswith("Urgent")))
        if op == "event_from_email" and self.event is None:
            m = re.search(r"put '([^']+)' in the calendar on (\S+) at (\d{2}:\d{2})", obs.text)
            self.event = {"title": m[1], "date": m[2], "time": m[3]} if m else None
        if op == "create":
            self.event = {k: self.goal[k] for k in ("title", "date", "time")}
        if path != "/calendar":
            return Action("click_mark", mark=self._pick(obs, lambda n: n == "Calendar"))
        assert self.event
        if f"{self.event['title']} | {self.event['date']} {self.event['time']}" in obs.text:
            return Action("done")
        for name in ("Title", "Date", "Time"):
            if name not in self.done_fill:
                self.done_fill.add(name)
                return Action(
                    "fill_mark",
                    mark=self._pick(obs, lambda n, x=name: n == x),  # type: ignore[misc]
                    text=self.event[name.lower()],
                )
        if self.saved:
            self.done_fill.clear()
        self.saved = True
        return Action("click_mark", mark=self._pick(obs, lambda n: n == "Save event"))


@dataclass
class TaskResult:
    task: str
    seed: int
    attempts: list[bool]

    def pass_at(self, k: int) -> float:
        return pass_at_k(len(self.attempts), sum(self.attempts), k)


def run_bench(
    seeds: range = range(1), attempts: int = 3, slip: float = 0.0, max_steps: int = 12,
    approve: bool = True, templates: list[Template] = TEMPLATES, b: Browser | None = None,
) -> list[TaskResult]:  # fmt: skip
    if b is None:
        with browser() as own:
            return run_bench(seeds, attempts, slip, max_steps, approve, templates, own)
    results = []
    if True:
        for t in templates:
            for seed in seeds:
                ok = []
                for attempt in range(attempts):
                    with SandboxApp(seed=seed) as app:
                        goal = t.params(random.Random(seed), app)
                        page = fresh_page(b)
                        pol = GoalPolicy(goal, random.Random(seed * 100 + attempt), slip)
                        guard = Guard(confirm=lambda what: approve and t.needs_confirmation)  # noqa: B023
                        answers: list[str] = []
                        orig = pol.next

                        def spy(
                            obs: Obs,
                            orig: Callable[[Obs], Action] = orig,
                            answers: list[str] = answers,
                        ) -> Action:
                            a = orig(obs)
                            if a.kind == "done":
                                answers.append(a.text)
                            return a

                        pol.next = spy  # type: ignore[method-assign]
                        run_episode(app, page, pol, "hybrid", guard, max_steps=max_steps)
                        page.context.close()
                        ok.append(t.check(app, goal, answers[-1] if answers else ""))
                results.append(TaskResult(t.name, seed, ok))
    return results


def summary(results: list[TaskResult], k: int, max_steps: int) -> str:
    p1 = sum(r.pass_at(1) for r in results) / len(results)
    pk = sum(r.pass_at(k) for r in results) / len(results)
    return f"pass@1 {p1:.2f}, pass@{k} {pk:.2f} over {len(results)} task instances (step budget {max_steps})"  # noqa: E501


if __name__ == "__main__":
    res = run_bench(seeds=range(2), attempts=3, slip=0.15)
    for r in res:
        print(r.task, r.seed, r.attempts)
    print(summary(res, 3, 12))
