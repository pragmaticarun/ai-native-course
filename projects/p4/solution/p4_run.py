"""P4 milestones 4-6: drive the workflow (approvals that arrive later, a killed worker,
replaying old histories) and score a suite of incidents.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from p4_activities import TriageActivities
from p4_kit import Decision, TriageResult, World
from p4_workflow import TASK_QUEUE, TriageWorkflow
from temporalio.client import Client, WorkflowHistory
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker


@dataclass
class Plan:
    """What the human does: decide after `after` (None = never), approve or not, maybe edit."""

    after: timedelta | None = timedelta(hours=2)
    approve: bool = True
    change: dict[str, Any] | None = None
    approver: str = "oncall@larkspur.test"


async def run_incident(
    env: WorkflowEnvironment, world: World, incident_id: str, plan: Plan, **acts_kw: Any
) -> TriageResult:
    """Run one incident in a time-skipping environment; the decision arrives `plan.after`
    later (in workflow time: hours or days pass in milliseconds)."""
    acts = TriageActivities(world, **acts_kw)
    async with Worker(
        env.client, task_queue=TASK_QUEUE, workflows=[TriageWorkflow], activities=acts.all()
    ):
        handle = await env.client.start_workflow(
            TriageWorkflow.run,
            incident_id,
            id=f"{incident_id}-{uuid.uuid4().hex[:6]}",
            task_queue=TASK_QUEUE,
        )
        if plan.after is not None:
            await env.sleep(plan.after)
            state = await handle.query(TriageWorkflow.state)
            if state["status"] == "waiting_for_approval":
                await handle.signal(
                    TriageWorkflow.decide, Decision(plan.approver, plan.approve, plan.change)
                )
        return await handle.result()


async def run_suite(world: World, plans: dict[str, Plan], **acts_kw: Any) -> list[TriageResult]:
    out = []
    async with await WorkflowEnvironment.start_time_skipping() as env:
        for incident_id, plan in plans.items():
            out.append(await run_incident(env, world, incident_id, plan, **acts_kw))
    return out


async def kill_and_resume(db: Path, incident_id: str) -> tuple[TriageResult, list[str]]:
    """Worker A (a subprocess) applies the fix, then hangs; we kill -9 it; worker B finishes.
    Returns the result and the order of apply attempts by worker."""
    world = World(db)
    worker_py = Path(__file__).with_name("p4_worker.py")
    async with await WorkflowEnvironment.start_local() as env:
        target = env.client.service_client.config.target_host
        a = subprocess.Popen(
            [sys.executable, str(worker_py), target, str(db), "A", "--hang-after-apply"]
        )
        try:
            handle = await env.client.start_workflow(
                TriageWorkflow.run,
                incident_id,
                id=f"kill-{uuid.uuid4().hex[:6]}",
                task_queue=TASK_QUEUE,
            )
            await handle.signal(TriageWorkflow.decide, Decision("oncall@larkspur.test", True))
            for _ in range(300):
                if world.changes():
                    break
                await asyncio.sleep(0.1)
            os.kill(a.pid, signal.SIGKILL)
        finally:
            a.wait()
        acts = TriageActivities(world, worker="B")
        async with Worker(
            env.client, task_queue=TASK_QUEUE, workflows=[TriageWorkflow], activities=acts.all()
        ):
            result = await handle.result()
    with world._db() as conn:
        workers = [
            r[0]
            for r in conn.execute(
                "SELECT worker FROM attempts WHERE key = ? ORDER BY at", (f"{incident_id}:apply",)
            )
        ]
    return result, workers


async def record_history(
    workflow_cls: type, world: World, incident_id: str, plan: Plan
) -> WorkflowHistory:
    """Run `workflow_cls` (e.g. the deployed v0) to completion and export its history."""
    acts = TriageActivities(world)
    async with await WorkflowEnvironment.start_time_skipping() as env:
        client: Client = env.client
        async with Worker(
            client, task_queue=TASK_QUEUE, workflows=[workflow_cls], activities=acts.all()
        ):
            wid = f"hist-{uuid.uuid4().hex[:6]}"
            handle = await client.start_workflow(
                "Triage", incident_id, id=wid, task_queue=TASK_QUEUE
            )
            if plan.after is not None:
                await env.sleep(plan.after)
                await handle.signal("decide", Decision(plan.approver, plan.approve, plan.change))
            await handle.result()
            return await handle.fetch_history()


async def replay_check(history: WorkflowHistory, workflow_cls: type) -> str | None:
    """None if `workflow_cls` replays the history cleanly, else the error text."""
    try:
        await Replayer(workflows=[workflow_cls]).replay_workflow(history)
        return None
    except Exception as e:  # noqa: BLE001 - we report whatever the replayer raised
        return f"{type(e).__name__}: {e}"
