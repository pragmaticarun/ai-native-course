"""A triage worker in its own process, so the evals can `kill -9` it mid-activity.

Usage: p4_worker.py <temporal-target> <world.db> <worker-name> [--hang-after-apply]
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(_HERE), str(_HERE.parent / "common")]

from p4_activities import TriageActivities  # noqa: E402
from p4_kit import World  # noqa: E402
from p4_workflow import TASK_QUEUE, TriageWorkflow  # noqa: E402
from temporalio.client import Client  # noqa: E402
from temporalio.worker import Worker  # noqa: E402


async def main(target: str, db: str, name: str, hang: bool) -> None:
    client = await Client.connect(target)
    acts = TriageActivities(World(db), worker=name, hang_after_apply=hang)
    async with Worker(
        client, task_queue=TASK_QUEUE, workflows=[TriageWorkflow], activities=acts.all()
    ):
        await asyncio.Event().wait()  # run until killed


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3], "--hang-after-apply" in sys.argv))
