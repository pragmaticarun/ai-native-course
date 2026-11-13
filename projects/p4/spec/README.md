# P4 — Durable triage & remediation workflow (Temporal)

**After:** M7–M8 · **Language:** Python, temporalio 1.36.0 · Temporal's local test servers
(downloaded by the SDK on first use), mock model, no cloud account

An incident report comes in. The workflow classifies it, gathers logs (a flaky tool, so
retries), proposes a config change from the logs, and asks a human. The decision is a
signal that may arrive days later; a reminder goes out after one day and the request
expires after three. An approved (possibly edited) change is applied, verified by a health
check, and rolled back if it doesn't help. Incidents with no safe change are escalated.

All side effects (config changes, notifications) go through a SQLite "world" under
idempotency keys, so the evals can check they happen exactly once, even when a worker is
killed with `SIGKILL` right after applying a change. The incidents are fictional (an invented
company, Larkspur Pay).

## Milestones

| # | File | You build | Evals |
|---|---|---|---|
| M1 | `p4_workflow.py` | the pipeline: classify → gather logs (retried) → propose → escalate or ask | `test_happy_path_*`, `test_transient_*`, `test_no_safe_change_*` |
| M2 | `p4_activities.py` | activities with stable idempotency keys; model calls as activities | `test_model_calls_are_recorded_*` |
| M3 | `p4_workflow.py` | the human gate: signal + query, reminder at 1 day, expiry at 3, reject, edit, rollback | `test_nothing_changes_*`, `test_approval_two_days_*`, `test_no_decision_*`, `test_rejection_*`, `test_an_edited_change_*` |
| M4 | `p4_run.py`, `p4_worker.py` | survive `kill -9` mid-activity; keep v1 replay-compatible with the deployed v0 (`workflow.patched`) | `test_killed_worker_*`, `test_v1_replays_v0_histories` |
| M5 | `p4_slo.py` | the suite: accuracy, statuses, SLOs (proposal ≤ 15 min, apply ≤ 30 min after approval, no unapproved changes) | `test_suite_meets_slos` |

## Done when

All evals pass with `PROJECT_VARIANT=solution`.

## Stretch (not built here)

A TypeScript worker (`@temporalio/worker` 1.25.0) for the same workflow; a real model behind
`MockTriageModel`; OpenTelemetry interceptors; Temporal Cloud or a self-hosted cluster;
worker versioning (build IDs) instead of `patched`.
