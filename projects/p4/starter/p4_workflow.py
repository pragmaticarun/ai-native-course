"""STARTER. TODO: the reminder, rollback and replay-safe versioning.

P4 milestones 1, 3 and 4: the triage workflow.

    classify -> gather_logs (retried) -> propose_fix
        -> no safe change: escalate to a human, stop
        -> notify approver -> wait for a decision (reminder after 1 day, expire after 3)
            -> rejected / expired: stop, nothing changed
            -> approved (optionally edited): apply_fix -> verify
                -> healthy: resolved        -> unhealthy: rollback -> rolled_back
        -> notify the owner (new in v1, behind `workflow.patched`)

The workflow is deterministic orchestration only: no I/O, no clocks except `workflow.now()`,
no randomness. A decision is a signal; it can arrive days later because waiting is durable
(a timer in Temporal's history, not a sleeping process).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from p4_activities import TriageActivities
    from p4_kit import (
        ChangeInput,
        Classification,
        Decision,
        Note,
        Proposal,
        ProposeInput,
        TriageResult,
    )

TASK_QUEUE = "p4-triage"
REMIND_AFTER = timedelta(days=1)
EXPIRE_AFTER = timedelta(days=3)
TIMEOUT = timedelta(seconds=30)
LOG_RETRY = RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)
HEARTBEAT = timedelta(seconds=2)  # how fast a dead worker is noticed
APPLY_RETRY = RetryPolicy(initial_interval=timedelta(milliseconds=200))


@workflow.defn(name="Triage")
class TriageWorkflow:
    def __init__(self) -> None:
        self.status = "started"
        self.decision: Decision | None = None
        self.proposal: Proposal | None = None

    @workflow.signal
    def decide(self, decision: Decision) -> None:
        if self.decision is None:  # first decision wins; later ones are ignored
            self.decision = decision

    @workflow.query
    def state(self) -> dict[str, Any]:
        p = self.proposal
        return {"status": self.status, "proposal": None if p is None else p.change}

    @workflow.run
    async def run(self, incident_id: str) -> TriageResult:
        t0 = workflow.now()
        timeline: dict[str, float] = {}

        def mark(name: str) -> None:
            timeline[name] = (workflow.now() - t0).total_seconds()

        acts = TriageActivities
        cls: Classification = await workflow.execute_activity_method(
            acts.classify, incident_id, start_to_close_timeout=TIMEOUT
        )
        mark("classified")
        self.status = "gathering_logs"
        logs = await workflow.execute_activity_method(
            acts.gather_logs, incident_id, retry_policy=LOG_RETRY, start_to_close_timeout=TIMEOUT
        )
        prop: Proposal = await workflow.execute_activity_method(
            acts.propose_fix, ProposeInput(incident_id, logs), start_to_close_timeout=TIMEOUT
        )
        self.proposal = prop
        mark("proposed")
        result = TriageResult(
            incident_id, "escalated", cls.category, cls.severity, prop.cause, timeline=timeline
        )

        if prop.change is None:
            await self._notify(
                f"{incident_id}:escalate",
                f"[{cls.severity}] {incident_id}: {prop.rationale}. Needs a human.",
            )
            return await self._close(result, mark)

        await self._notify(
            f"{incident_id}:approval",
            f"[{cls.severity}] {incident_id}: propose {prop.change} ({prop.rationale}). "
            "Approve, edit or reject.",
        )
        self.status = "waiting_for_approval"
        # TODO: wait REMIND_AFTER, send one reminder (key "<id>:reminder"), then wait the rest
        decided = await self._wait(EXPIRE_AFTER)
        mark("decided")
        if not decided or self.decision is None:
            result.status = "expired"
            return await self._close(result, mark)
        result.approver = self.decision.approver
        if not self.decision.approve:
            result.status = "rejected"
            return await self._close(result, mark)

        change = self.decision.change or prop.change
        self.status = "applying"
        previous = await workflow.execute_activity_method(
            acts.apply_fix,
            ChangeInput(incident_id, change),
            start_to_close_timeout=TIMEOUT,
            heartbeat_timeout=HEARTBEAT,
            retry_policy=APPLY_RETRY,
        )
        result.change = change
        mark("applied")
        ok = await workflow.execute_activity_method(
            acts.verify, incident_id, start_to_close_timeout=TIMEOUT
        )
        mark("verified")
        # TODO: if verification fails, roll back to `previous` and report "rolled_back"
        _ = (ok, previous, ChangeInput)
        result.status = "resolved"
        return await self._close(result, mark)

    async def _wait(self, timeout: timedelta) -> bool:
        try:
            await workflow.wait_condition(lambda: self.decision is not None, timeout=timeout)
            return True
        except TimeoutError:
            return False

    async def _notify(self, key: str, body: str) -> None:
        await workflow.execute_activity_method(
            TriageActivities.notify, Note(key, body), start_to_close_timeout=TIMEOUT
        )

    async def _close(self, result: TriageResult, mark: Any) -> TriageResult:
        self.status = result.status
        # TODO: v0 is already deployed without this step; gate it so v0 histories replay
        await self._notify(
            f"{result.incident_id}:owner", f"{result.incident_id} closed: {result.status}"
        )
        mark("closed")
        return result
