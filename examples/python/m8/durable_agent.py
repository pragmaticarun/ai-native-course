"""M8 worked example: kill the worker halfway through a 10-step agent run.

Each step of the agent's plan is a Temporal activity with a side effect (here: a row in
a SQLite "ledger" standing in for an email sent, a file uploaded, a ticket filed). The
workflow only orchestrates; Temporal records every completed activity in the history.

The demo (`run_demo`, also the test):
1. worker A runs in a subprocess; on step 6 it performs the side effect, then hangs;
2. we `kill -9` worker A, mid-activity;
3. worker B starts. Steps 1-5 are NOT re-run (their results are in the history); step 6
   times out on the dead worker (heartbeat timeout) and is retried on B, which finds the
   side effect already in the ledger under its idempotency key and does not repeat it.

Runs against Temporal's local dev server (`WorkflowEnvironment.start_local()`, which
downloads the Temporal CLI on first use). Tested with temporalio 1.36.0.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sqlite3
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TypedDict

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

PLAN = [
    "fetch_ticket", "pull_recording", "probe", "transcode", "transcribe",
    "upload", "summarise", "notify_owner", "label_ticket", "close_ticket",
]  # fmt: skip
TASK_QUEUE = "m8-durable-agent"


@dataclass
class StepInput:
    run_id: str
    index: int
    tool: str


class Ledger:
    """The outside world. `effects` must never get a duplicate; `attempts` may."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS effects (key TEXT PRIMARY KEY, result TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS attempts (key TEXT, worker TEXT, at REAL)")

    def attempt(self, key: str, worker: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO attempts VALUES (?, ?, ?)", (key, worker, time.time()))

    def effect_once(self, key: str, result: str) -> tuple[str, bool]:
        """Insert-if-absent under the idempotency key. Returns (result, newly_done)."""
        with sqlite3.connect(self.path) as db:
            cur = db.execute("INSERT OR IGNORE INTO effects VALUES (?, ?)", (key, result))
            if cur.rowcount == 1:
                return result, True
            row = db.execute("SELECT result FROM effects WHERE key = ?", (key,)).fetchone()
            return row[0], False

    def count(self, table: str) -> int:
        with sqlite3.connect(self.path) as db:
            return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def keys(self) -> list[str]:
        with sqlite3.connect(self.path) as db:
            return [r[0] for r in db.execute("SELECT key FROM attempts ORDER BY at")]


class AgentSteps:
    def __init__(self, ledger: Ledger, worker: str, hang_after_effect: int | None = None) -> None:
        self.ledger, self.worker, self.hang = ledger, worker, hang_after_effect

    @activity.defn(name="run_step")
    async def run_step(self, step: StepInput) -> str:
        key = f"{step.run_id}:{step.index}"  # idempotency key: stable across retries
        self.ledger.attempt(key, self.worker)
        result, _ = self.ledger.effect_once(key, f"{step.tool} ok")
        if step.index == self.hang:
            while True:  # simulate a worker that dies before reporting completion
                await asyncio.sleep(0.2)
        activity.heartbeat(step.index)
        return result


@workflow.defn
class AgentRun:
    @workflow.run
    async def run(self, run_id: str) -> list[str]:
        results = []
        for i, tool in enumerate(PLAN, start=1):
            results.append(
                await workflow.execute_activity(
                    "run_step",
                    StepInput(run_id, i, tool),
                    result_type=str,
                    start_to_close_timeout=timedelta(seconds=30),
                    heartbeat_timeout=timedelta(seconds=2),  # how fast a dead worker is noticed
                    retry_policy=RetryPolicy(initial_interval=timedelta(milliseconds=200)),
                )
            )
        return results


class DemoResult(TypedDict):
    results: list[str]
    effects: int
    attempts: int
    attempt_keys: list[str]


async def run_demo(ledger_path: str | Path) -> DemoResult:
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    ledger = Ledger(ledger_path)
    run_id = f"agent-{uuid.uuid4().hex[:8]}"
    async with await WorkflowEnvironment.start_local() as env:
        target = env.client.service_client.config.target_host
        worker_a = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).with_name("worker_proc.py")),
                target,
                str(ledger_path),
                "6",
            ],
        )
        try:
            handle = await env.client.start_workflow(
                AgentRun.run, run_id, id=run_id, task_queue=TASK_QUEUE
            )
            for _ in range(300):  # wait until worker A has done step 6's side effect
                if ledger.count("effects") >= 6:
                    break
                await asyncio.sleep(0.1)
            os.kill(worker_a.pid, signal.SIGKILL)
        finally:
            worker_a.wait()
        steps = AgentSteps(ledger, "B")
        async with Worker(
            env.client, task_queue=TASK_QUEUE, workflows=[AgentRun], activities=[steps.run_step]
        ):
            results = await handle.result()
    return {
        "results": results,
        "effects": ledger.count("effects"),
        "attempts": ledger.count("attempts"),
        "attempt_keys": [k.split(":")[1] for k in ledger.keys()],
    }


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out = asyncio.run(run_demo(Path(tmp) / "ledger.db"))
    print("steps completed:", len(out["results"]))  # type: ignore[arg-type]
    print("side effects:", out["effects"], "| activity attempts:", out["attempts"])
    print("attempt order:", " ".join(out["attempt_keys"]))  # type: ignore[arg-type]
