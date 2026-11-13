"""P4 kit (provided): v0 of the triage workflow, "already deployed in production".

Runs started on v0 may still be waiting for approval when v1 ships, so v1 must replay v0
histories without non-determinism errors (`evals/test_p4.py::test_v1_replays_v0_histories`).
v0 calls activities by name, so it doesn't import your activities module.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
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
class TriageWorkflowV0:
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

        cls = await workflow.execute_activity(
            "classify", incident_id, result_type=Classification, start_to_close_timeout=TIMEOUT
        )
        mark("classified")
        self.status = "gathering_logs"
        logs = await workflow.execute_activity(
            "gather_logs",
            incident_id,
            result_type=list[str],
            retry_policy=LOG_RETRY,
            start_to_close_timeout=TIMEOUT,
        )
        prop = await workflow.execute_activity(
            "propose_fix",
            ProposeInput(incident_id, logs),
            result_type=Proposal,
            start_to_close_timeout=TIMEOUT,
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
        decided = await self._wait(REMIND_AFTER)
        if not decided:
            await self._notify(
                f"{incident_id}:reminder", f"Reminder: {incident_id} awaits approval."
            )
            decided = await self._wait(EXPIRE_AFTER - REMIND_AFTER)
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
        previous = await workflow.execute_activity(
            "apply_fix",
            ChangeInput(incident_id, change),
            result_type=dict[str, Any],
            start_to_close_timeout=TIMEOUT,
            heartbeat_timeout=HEARTBEAT,
            retry_policy=APPLY_RETRY,
        )
        result.change = change
        mark("applied")
        ok = await workflow.execute_activity(
            "verify", incident_id, result_type=bool, start_to_close_timeout=TIMEOUT
        )
        mark("verified")
        if ok:
            result.status = "resolved"
        else:
            await workflow.execute_activity(
                "rollback",
                ChangeInput(incident_id, previous),
                start_to_close_timeout=TIMEOUT,
                heartbeat_timeout=HEARTBEAT,
                retry_policy=APPLY_RETRY,
            )
            result.status = "rolled_back"
        return await self._close(result, mark)

    async def _wait(self, timeout: timedelta) -> bool:
        try:
            await workflow.wait_condition(lambda: self.decision is not None, timeout=timeout)
            return True
        except TimeoutError:
            return False

    async def _notify(self, key: str, body: str) -> None:
        await workflow.execute_activity("notify", Note(key, body), start_to_close_timeout=TIMEOUT)

    async def _close(self, result: TriageResult, mark: Any) -> TriageResult:
        self.status = result.status
        mark("closed")
        return result
