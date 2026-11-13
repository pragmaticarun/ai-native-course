"""Records a real V1 history on Temporal's test server, then replays it against OrderV2."""

import asyncio
import uuid

from _impl import load
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, UnsandboxedWorkflowRunner, Worker

impl = load(__file__)
Q = "m8-ex3"
ACTS = [impl.charge, impl.fraud_check, impl.ship]


async def run_order(env, wf, order):
    async with Worker(env.client, task_queue=Q, workflows=[wf], activities=ACTS,
                      workflow_runner=UnsandboxedWorkflowRunner()):  # fmt: skip
        h = await env.client.start_workflow("Order", order, id=str(uuid.uuid4()), task_queue=Q,
                                            result_type=list[str])  # fmt: skip
        result = await h.result()
        return result, await h.fetch_history()


async def scenario():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        v1_result, v1_history = await run_order(env, impl.OrderV1, "A-1")
        v2_result, _ = await run_order(env, impl.OrderV2, "B-2")
    replayer = Replayer(workflows=[impl.OrderV2], workflow_runner=UnsandboxedWorkflowRunner())
    replay = await replayer.replay_workflow(v1_history, raise_on_replay_failure=False)
    return v1_result, v2_result, replay.replay_failure


def test_v2_replays_v1_and_adds_the_check_for_new_runs():
    v1_result, v2_result, failure = asyncio.run(scenario())
    assert v1_result == ["charged A-1", "shipped A-1"]
    assert failure is None, f"V1 history no longer replays: {failure}"
    assert v2_result == ["charged B-2", "checked B-2", "shipped B-2"]
