"""STARTER. TODO: a stable idempotency key for apply_fix.

P4 milestone 2: activities, the only code that touches the outside world.

Every side effect goes through `World` under an idempotency key derived from the incident
(never from the attempt), so a retried or re-run activity finds its own earlier effect and
doesn't repeat it. Model calls are activities too: they're slow, can fail, and their
results must be recorded in the history so a replay doesn't call the model again.
"""

from __future__ import annotations

import asyncio
from typing import Any

from p4_kit import (
    BY_ID,
    ChangeInput,
    Classification,
    MockTriageModel,
    Note,
    Proposal,
    ProposeInput,
    World,
    fetch_logs,
    healthy,
)
from temporalio import activity


class TriageActivities:
    def __init__(
        self,
        world: World,
        model: MockTriageModel | None = None,
        worker: str = "A",
        flaky_logs: bool = False,
        hang_after_apply: bool = False,
    ) -> None:
        self.world, self.model = world, model or MockTriageModel()
        self.worker, self.flaky, self.hang = worker, flaky_logs, hang_after_apply

    @activity.defn
    async def classify(self, incident_id: str) -> Classification:
        inc = BY_ID[incident_id]
        return self.model.classify(inc["title"], inc["report"])

    @activity.defn
    async def gather_logs(self, incident_id: str) -> list[str]:
        return fetch_logs(self.world, incident_id, flaky=self.flaky)

    @activity.defn
    async def propose_fix(self, inp: ProposeInput) -> Proposal:
        inc = BY_ID[inp.incident_id]
        return self.model.propose(inc["service"], self.world.config(inc["service"]), inp.logs)

    @activity.defn
    async def notify(self, note: Note) -> bool:
        return self.world.send_once(note.key, note.body)

    @activity.defn
    async def apply_fix(self, inp: ChangeInput) -> dict[str, Any]:
        # TODO: the key must be stable across retries and workers (derive it from the incident only)
        key = f"{inp.incident_id}:apply:{activity.info().attempt}"
        self.world.attempt(key, self.worker)
        previous, _ = self.world.apply_once(key, BY_ID[inp.incident_id]["service"], inp.change)
        if self.hang:  # simulate a worker that dies after the effect, before reporting it
            while True:
                await asyncio.sleep(0.2)
        return previous

    @activity.defn
    async def verify(self, incident_id: str) -> bool:
        return healthy(self.world, incident_id)

    @activity.defn
    async def rollback(self, inp: ChangeInput) -> dict[str, Any]:
        key = f"{inp.incident_id}:rollback"
        self.world.attempt(key, self.worker)
        previous, _ = self.world.apply_once(key, BY_ID[inp.incident_id]["service"], inp.change)
        return previous

    def all(self) -> list[Any]:
        return [
            self.classify,
            self.gather_logs,
            self.propose_fix,
            self.notify,
            self.apply_fix,
            self.verify,
            self.rollback,
        ]
