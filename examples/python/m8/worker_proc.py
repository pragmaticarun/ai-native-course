"""Worker A for durable_agent.py, in its own process so the demo can `kill -9` it.

Usage: worker_proc.py <temporal-target> <ledger-path> <hang-after-step>
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from durable_agent import TASK_QUEUE, AgentRun, AgentSteps, Ledger  # noqa: E402
from temporalio.client import Client  # noqa: E402
from temporalio.worker import Worker  # noqa: E402


async def main(target: str, ledger_path: str, hang: int) -> None:
    client = await Client.connect(target)
    steps = AgentSteps(Ledger(ledger_path), "A", hang_after_effect=hang)
    async with Worker(
        client, task_queue=TASK_QUEUE, workflows=[AgentRun], activities=[steps.run_step]
    ):
        await asyncio.Event().wait()  # run until killed


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3])))
