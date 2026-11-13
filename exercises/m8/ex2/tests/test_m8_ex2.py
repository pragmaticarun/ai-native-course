"""Runs on Temporal's time-skipping test server (downloaded by temporalio on first use)."""

import asyncio
import uuid
from datetime import timedelta

import pytest
from _impl import load
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

impl = load(__file__)
Q = "m8-ex2"


async def scenario(after: timedelta, signal: tuple[str, str] | None):
    async with await WorkflowEnvironment.start_time_skipping() as env:
        # Unsandboxed: the exercise module is loaded from a file path, which the
        # workflow sandbox cannot re-import by name.
        async with Worker(env.client, task_queue=Q, workflows=[impl.PublishWithApproval],
                          workflow_runner=UnsandboxedWorkflowRunner()):  # fmt: skip
            h = await env.client.start_workflow(
                "PublishWithApproval",
                "Release 2.0",
                id=str(uuid.uuid4()),
                task_queue=Q,
                result_type=str,
            )
            await env.sleep(after)
            before = await h.query("status")
            if signal:
                await h.signal(signal[0], signal[1])
            return before, await h.result(), await h.query("status")


def test_approved_three_days_later():
    before, result, after = asyncio.run(scenario(timedelta(days=3), ("approve", "asha")))
    assert before == "waiting"
    assert result == "published Release 2.0 (approved by asha)" and after == "approved"


def test_rejected():
    _, result, after = asyncio.run(scenario(timedelta(hours=5), ("reject", "wrong thumbnail")))
    assert result == "rejected: wrong thumbnail" and after == "rejected"


def test_expires_after_seven_days():
    _, result, after = asyncio.run(scenario(timedelta(days=8), None))
    assert result == "expired" and after == "expired"


@pytest.mark.parametrize("days", [6])
def test_still_waiting_before_the_deadline(days):
    before, result, _ = asyncio.run(scenario(timedelta(days=days), ("approve", "li")))
    assert before == "waiting" and result.startswith("published")
