"""P4 milestone 6: score the suite like an on-call team would.

SLOs (ours, for this exercise): a proposal within 15 minutes of the report; a fix applied
within 30 minutes of approval; zero changes without an approval; every applied change
either verified healthy or rolled back. Times are workflow time, so they're exact even
though the tests skip days in milliseconds.
"""

from __future__ import annotations

from typing import Any

from p4_kit import BY_ID, TriageResult, World

PROPOSE_WITHIN_S = 15 * 60
APPLY_WITHIN_S = 30 * 60


def score(results: list[TriageResult], world: World) -> dict[str, Any]:
    approved = [r for r in results if r.status in ("resolved", "rolled_back")]
    applied_ids = {k.split(":")[0] for k in world.changes() if k.endswith(":apply")}
    unapproved = sorted(applied_ids - {r.incident_id for r in approved})
    cls_ok = sum(r.category == BY_ID[r.incident_id]["gold"]["category"] for r in results)
    cause_ok = sum(r.cause == BY_ID[r.incident_id]["gold"]["cause"] for r in results)
    return {
        "incidents": len(results),
        "classification_accuracy": round(cls_ok / len(results), 3),
        "cause_accuracy": round(cause_ok / len(results), 3),
        "statuses": {
            s: sum(r.status == s for r in results) for s in sorted({r.status for r in results})
        },
        "proposal_slo_met": all(r.timeline["proposed"] <= PROPOSE_WITHIN_S for r in results),
        "apply_slo_met": all(
            r.timeline["applied"] - r.timeline["decided"] <= APPLY_WITHIN_S for r in approved
        ),
        "unapproved_changes": unapproved,
        "unverified_changes": [
            r.incident_id for r in approved if r.status not in ("resolved", "rolled_back")
        ],
        "approval_wait_h": {
            r.incident_id: round((r.timeline["decided"] - r.timeline["proposed"]) / 3600, 2)
            for r in results
            if "decided" in r.timeline
        },
    }


def table(results: list[TriageResult]) -> str:
    rows = [
        "| incident | category | cause | status | change | wait (h) |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        wait = (
            (r.timeline["decided"] - r.timeline["proposed"]) / 3600
            if "decided" in r.timeline
            else 0
        )
        rows.append(
            f"| {r.incident_id} | {r.category} | {r.cause} | {r.status} "
            f"| {r.change or '-'} | {wait:.1f} |"
        )
    return "\n".join(rows)
