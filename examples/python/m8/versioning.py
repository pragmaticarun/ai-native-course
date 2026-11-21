"""L8.5: versioning a workflow without breaking in-flight runs, checked by replay.

Temporal re-runs workflow code against the recorded history ("replay") whenever a worker
picks up a run. If new code schedules a different command at the same point, replay fails
with a non-determinism error. So a change like "add a review step" must be gated:

    if workflow.patched("add-review"):   # True for new runs, False when replaying old ones
        await review(...)

`replay_check` records a history with v1, then replays it against a candidate v2. This is
the same check you would run in CI against histories exported from production.

`sdk_flags` lists the SDK "logic flags" a history recorded. The SDK sets a flag the first time
a run uses a behaviour change, and replay keeps honouring it, so one worker can run old and new
histories side by side. temporalio 1.36.0 turned flag 2 (single-batch activation) on for new
runs; 1.36.1 turned it off again by default. Histories that already recorded flag 2 keep it.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import WorkflowHistory
from temporalio.worker import Replayer, Worker

TIMEOUT = timedelta(seconds=30)


@activity.defn
async def transcode(name: str) -> str:
    return f"{name}.mp4"


@activity.defn
async def review(name: str) -> str:
    return f"reviewed {name}"


@activity.defn
async def publish(name: str) -> str:
    return f"published {name}"


@workflow.defn(name="Publish")
class PublishV1:
    @workflow.run
    async def run(self, name: str) -> list[str]:
        out = [await workflow.execute_activity(transcode, name, start_to_close_timeout=TIMEOUT)]
        out.append(await workflow.execute_activity(publish, out[0], start_to_close_timeout=TIMEOUT))
        return out


@workflow.defn(name="Publish")
class PublishV2Unsafe:
    """Inserts the new step unconditionally: breaks every run started on v1."""

    @workflow.run
    async def run(self, name: str) -> list[str]:
        out = [await workflow.execute_activity(transcode, name, start_to_close_timeout=TIMEOUT)]
        out.append(await workflow.execute_activity(review, out[0], start_to_close_timeout=TIMEOUT))
        out.append(await workflow.execute_activity(publish, out[0], start_to_close_timeout=TIMEOUT))
        return out


@workflow.defn(name="Publish")
class PublishV2:
    @workflow.run
    async def run(self, name: str) -> list[str]:
        out = [await workflow.execute_activity(transcode, name, start_to_close_timeout=TIMEOUT)]
        if workflow.patched("add-review"):
            out.append(
                await workflow.execute_activity(review, out[0], start_to_close_timeout=TIMEOUT)
            )
        out.append(await workflow.execute_activity(publish, out[0], start_to_close_timeout=TIMEOUT))
        return out


async def record_history(client, workflow_cls, name: str = "talk") -> WorkflowHistory:
    wid = f"publish-{uuid.uuid4().hex[:8]}"
    async with Worker(client, task_queue="m8-versioning", workflows=[workflow_cls],
                      activities=[transcode, review, publish]):  # fmt: skip
        handle = await client.start_workflow(
            workflow_cls.run, name, id=wid, task_queue="m8-versioning"
        )
        await handle.result()
    return await handle.fetch_history()


def sdk_flags(history: WorkflowHistory) -> set[int]:
    """The SDK logic flags recorded in a history's completed workflow tasks."""
    flags: set[int] = set()
    for event in history.events:
        if event.HasField("workflow_task_completed_event_attributes"):
            meta = event.workflow_task_completed_event_attributes.sdk_metadata
            flags.update(meta.lang_used_flags)
    return flags


async def replay_check(history: WorkflowHistory, candidate) -> str | None:
    """None if `candidate` can replay `history`, else the failure message."""
    try:
        await Replayer(workflows=[candidate]).replay_workflow(history)
        return None
    except Exception as exc:  # temporalio raises a NondeterminismError subclass
        return f"{type(exc).__name__}: {exc}"
