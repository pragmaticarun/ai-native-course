"""P4 evals: a durable triage workflow on Temporal's local test servers (downloaded by the
temporalio SDK on first use; no cloud account). Time-skipping makes "approval arrives two
days later" take milliseconds.

PROJECT_VARIANT=starter|solution pytest projects/p4/evals
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from p4_kit import BY_ID, INCIDENTS, MockTriageModel, World
from p4_legacy import TriageWorkflowV0
from p4_run import Plan, kill_and_resume, record_history, replay_check, run_incident, run_suite
from p4_slo import score, table
from p4_workflow import TriageWorkflow
from temporalio.testing import WorkflowEnvironment


@pytest.fixture
def world(tmp_path) -> World:
    w = World(tmp_path / "world.db")
    for inc in INCIDENTS:
        w.seed(inc)
    return w


def one(world: World, incident_id: str, plan: Plan, **kw):
    async def go():
        async with await WorkflowEnvironment.start_time_skipping() as env:
            return await run_incident(env, world, incident_id, plan, **kw)

    return asyncio.run(go())


# ------------------------------------------------------------------ M1-M2 pipeline + activities
def test_happy_path_classifies_proposes_applies_and_verifies(world):
    r = one(world, "INC-101", Plan())
    assert (r.status, r.category, r.cause) == ("resolved", "latency", "timeout_too_low")
    assert world.config("checkout")["timeout_ms"] == 2000
    keys = [k for k, _ in world.outbox("INC-101")]
    assert keys == ["INC-101:approval", "INC-101:owner"]


def test_transient_log_errors_are_retried(world):
    r = one(world, "INC-103", Plan(), flaky_logs=True)
    assert r.status == "resolved"
    with world._db() as db:
        assert (
            db.execute("SELECT COUNT(*) FROM log_calls WHERE incident='INC-103'").fetchone()[0] == 2
        )


def test_model_calls_are_recorded_not_repeated(world):
    model = MockTriageModel()
    one(world, "INC-106", Plan(), model=model)
    assert model.calls == ["classify", "propose"]


# ------------------------------------------------------------------ M3 human in the loop
def test_nothing_changes_before_approval(world):
    async def go():
        async with await WorkflowEnvironment.start_time_skipping() as env:
            from p4_activities import TriageActivities
            from p4_workflow import TASK_QUEUE
            from temporalio.worker import Worker

            async with Worker(
                env.client,
                task_queue=TASK_QUEUE,
                workflows=[TriageWorkflow],
                activities=TriageActivities(world).all(),
            ):
                h = await env.client.start_workflow(
                    TriageWorkflow.run, "INC-102", id="w1", task_queue=TASK_QUEUE
                )
                await env.sleep(timedelta(hours=5))
                state = await h.query(TriageWorkflow.state)
                changed = world.changes()
                await h.terminate()
                return state, changed

    state, changed = asyncio.run(go())
    assert state == {"status": "waiting_for_approval", "proposal": {"pool_size": 40}}
    assert changed == []


def test_approval_two_days_later_sends_one_reminder(world):
    r = one(world, "INC-104", Plan(after=timedelta(days=2)))
    assert r.status == "resolved"
    assert [k for k, _ in world.outbox("INC-104")].count("INC-104:reminder") == 1
    assert r.timeline["decided"] - r.timeline["proposed"] == pytest.approx(48 * 3600, abs=60)


def test_no_decision_expires_after_three_days_without_changes(world):
    r = one(world, "INC-108", Plan(after=None))
    assert r.status == "expired" and world.changes() == []
    assert r.timeline["decided"] - r.timeline["proposed"] == pytest.approx(72 * 3600, abs=60)


def test_rejection_changes_nothing(world):
    r = one(world, "INC-105", Plan(approve=False))
    assert r.status == "rejected" and world.config("partner-api")["rate_limit_rps"] == 200


def test_an_edited_change_that_fails_verification_is_rolled_back(world):
    r = one(world, "INC-102", Plan(change={"pool_size": 12}))
    assert r.status == "rolled_back" and r.change == {"pool_size": 12}
    assert world.config("ledger")["pool_size"] == 10
    assert world.changes() == ["INC-102:apply", "INC-102:rollback"]


def test_no_safe_change_escalates_to_a_human(world):
    r = one(world, "INC-107", Plan())
    assert r.status == "escalated" and world.changes() == []
    assert "Needs a human" in dict(world.outbox("INC-107"))["INC-107:escalate"]


# ------------------------------------------------------------------ M4 durability + versioning
def test_killed_worker_resumes_without_reapplying(tmp_path):
    db = tmp_path / "kill.db"
    w = World(db)
    for inc in INCIDENTS:
        w.seed(inc)
    result, workers = asyncio.run(kill_and_resume(db, "INC-101"))
    assert result.status == "resolved"
    assert workers == ["A", "B"]  # retried on B after A died...
    assert w.changes() == ["INC-101:apply"]  # ...but applied exactly once
    assert w.config("checkout")["timeout_ms"] == 2000


@pytest.mark.parametrize("plan", [Plan(), Plan(approve=False)], ids=["approved", "rejected"])
def test_v1_replays_v0_histories(world, plan):
    history = asyncio.run(record_history(TriageWorkflowV0, world, "INC-106", plan))
    assert asyncio.run(replay_check(history, TriageWorkflow)) is None


# ------------------------------------------------------------------ M5 suite + SLOs
def test_suite_meets_slos(world):
    plans = {i["id"]: Plan() for i in INCIDENTS}
    plans |= {
        "INC-104": Plan(after=timedelta(days=2)),
        "INC-105": Plan(approve=False),
        "INC-108": Plan(after=None),
        "INC-102": Plan(change={"pool_size": 12}),
    }
    results = asyncio.run(run_suite(world, plans, flaky_logs=True))
    s = score(results, world)
    assert s["classification_accuracy"] == 1.0 and s["cause_accuracy"] == 1.0
    assert s["statuses"] == {
        "escalated": 1,
        "expired": 1,
        "rejected": 1,
        "resolved": 4,
        "rolled_back": 1,
    }
    assert s["proposal_slo_met"] and s["apply_slo_met"]
    assert s["unapproved_changes"] == [] and s["unverified_changes"] == []
    assert "| INC-104 | availability | out_of_memory | resolved |" in table(results)


def test_gold_labels_are_consistent():
    assert {i["gold"]["fix"] is None for i in INCIDENTS} == {True, False}
    assert all(i["gold"]["fix"] is None or i["healthy_if"] for i in INCIDENTS)
    assert set(BY_ID) == {f"INC-{n}" for n in range(101, 109)}
