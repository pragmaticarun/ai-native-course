"""P8 milestone 5: the 20-task harness, recordings, replay, metrics and failure taxonomy.

`record()` runs the scripted planner live through each adapter's wire format and saves every
model turn; `replay()` feeds those turns back through the same graph (what CI does). Because
the environments are deterministic, a replay must reproduce the recorded outcome exactly.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any

from gui_eval_harness import pass_at_k
from p8_adapters import ADAPTERS
from p8_graph import Budget, build, drive
from p8_kit import (
    BY_ID,
    TASKS,
    USD_PER_1K_TOKENS,
    EnvCrashed,
    MobileEnv,
    Obs,
    ReplayModel,
    ScriptedPlanner,
    WebEnv,
    check,
    trajectory_path,
)

SEEDS = (0, 1, 2)
BUDGETS = {"web": Budget(max_steps=8), "mobile": Budget(max_steps=10)}


@dataclass
class RecordingModel:
    planner: ScriptedPlanner
    adapter: str
    turns: list[dict[str, Any]] = field(default_factory=list)

    def next(self, obs: Obs, feedback: Any) -> dict[str, Any]:
        steps = self.planner.decide(obs)
        turn = ADAPTERS[self.adapter].encode(steps, obs, self.planner.slipped, len(self.turns))
        self.turns.append(turn)
        return turn


class CrashingEnv:
    """Wraps an env and drops the connection once, on the Nth observation."""

    def __init__(self, env: Any, at: int) -> None:
        self.env, self.at, self.n = env, at, 0
        self.name = env.name

    def observe(self) -> Obs:
        self.n += 1
        if self.n == self.at:
            self.env.crash_next_observe()
        return self.env.observe()  # type: ignore[no-any-return]

    def __getattr__(self, k: str) -> Any:
        return getattr(self.env, k)


@dataclass
class Result:
    task: str
    adapter: str
    seed: int
    success: bool
    why: str
    status: str
    steps: int
    invalid: int
    blocked: int
    interventions: int
    recoveries: int
    tokens: int
    seconds: float
    answer: str
    resumed: bool = False

    @property
    def usd(self) -> float:
        return self.tokens / 1000 * USD_PER_1K_TOKENS

    def outcome(self) -> dict[str, Any]:
        """The part a replay must reproduce exactly (not time)."""
        d = asdict(self)
        d.pop("seconds")
        d.pop("resumed")
        return d


def make_env(task: dict[str, Any], browser: Any) -> Any:
    return WebEnv(browser, task) if task["env"] == "web" else MobileEnv(task)


def run_one(
    task_id: str,
    adapter: str,
    seed: int,
    model: Any,
    browser: Any,
    crash_at: int | None = None,
    budget: Budget | None = None,
) -> Result:
    task = BY_ID[task_id]
    env = make_env(task, browser)
    t = time.perf_counter()
    try:
        runner = CrashingEnv(env, crash_at) if crash_at else env
        graph = build(runner, model, adapter, budget or BUDGETS[task["env"]])
        thread = f"{task_id}-{adapter}-{seed}"
        resumed = False
        try:
            out, _ = drive(graph, task["goal"], thread, task["human"])
        except EnvCrashed:  # resume the same thread from its last checkpoint
            resumed = True
            out, _ = drive(graph, task["goal"], thread, task["human"], resume=True)
        ok, why = check(task, env, out.get("answer", ""))
        return Result(
            task_id,
            adapter,
            seed,
            ok,
            why,
            out.get("status", "?"),
            out.get("step", 0),
            out.get("invalid", 0),
            len(out.get("blocked", [])),
            out.get("interventions", 0),
            len(out.get("recoveries", [])),
            out.get("tokens", 0),
            time.perf_counter() - t,
            out.get("answer", ""),
            resumed,
        )
    finally:
        env.close()


def record(
    browser: Any, adapters: tuple[str, ...] = tuple(ADAPTERS), tasks: list[str] | None = None
) -> list[Result]:
    results = []
    for adapter in adapters:
        for tid in tasks or [t["id"] for t in TASKS]:
            for seed in SEEDS:
                model = RecordingModel(ScriptedPlanner(BY_ID[tid], seed), adapter)
                r = run_one(tid, adapter, seed, model, browser)
                p = trajectory_path(adapter, tid, seed)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(
                    json.dumps(
                        {
                            "task": tid,
                            "adapter": adapter,
                            "seed": seed,
                            "turns": model.turns,
                            "outcome": r.outcome(),
                        },
                        indent=1,
                    )
                    + "\n"
                )
                results.append(r)
    return results


def load(adapter: str, task_id: str, seed: int) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(trajectory_path(adapter, task_id, seed).read_text())
    return data


def replay(
    browser: Any, adapters: tuple[str, ...] = tuple(ADAPTERS), tasks: list[str] | None = None
) -> list[Result]:
    results = []
    for adapter in adapters:
        for tid in tasks or [t["id"] for t in TASKS]:
            for seed in SEEDS:
                rec = load(adapter, tid, seed)
                results.append(run_one(tid, adapter, seed, ReplayModel(rec["turns"]), browser))
    return results


def taxonomy(r: Result) -> str | None:
    if r.success:
        return None
    if r.why.startswith("unrequested side effect"):
        return "safety"
    if r.status == "done":
        return "verification"  # claimed success, state says otherwise
    if r.invalid >= 3:
        return "grounding"
    return "planning"


def metrics(results: list[Result]) -> list[dict[str, Any]]:
    rows = []
    for adapter in dict.fromkeys(r.adapter for r in results):
        rs = [r for r in results if r.adapter == adapter]
        tasks = sorted({r.task for r in rs})
        per = {t: [r for r in rs if r.task == t] for t in tasks}
        fails = [c for r in rs if (c := taxonomy(r))]
        rows.append(
            {
                "adapter": adapter,
                "pass@1": round(
                    mean(pass_at_k(len(v), sum(r.success for r in v), 1) for v in per.values()), 3
                ),
                "pass@3": round(
                    mean(pass_at_k(len(v), sum(r.success for r in v), 3) for v in per.values()), 3
                ),
                "runs": len(rs),
                "mean_steps": round(mean(r.steps for r in rs), 1),
                "invalid_actions": sum(r.invalid for r in rs),
                "unsafe_blocked": sum(r.blocked for r in rs),
                "interventions": sum(r.interventions for r in rs),
                "recoveries": sum(r.recoveries for r in rs),
                "usd (placeholder)": round(sum(r.usd for r in rs), 3),
                "seconds": round(sum(r.seconds for r in rs), 1),
                "failures": {c: fails.count(c) for c in sorted(set(fails))},
            }
        )
    return rows


def markdown(rows: list[dict[str, Any]]) -> str:
    keys = list(rows[0])
    out = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    out += ["| " + " | ".join(str(r[k]) for k in keys) + " |" for r in rows]
    return "\n".join(out)


if __name__ == "__main__":  # re-record: cd python && uv run python ../projects/p8/solution/p8_harness.py
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        res = record(b)
        b.close()
    print(markdown(metrics(res)))
