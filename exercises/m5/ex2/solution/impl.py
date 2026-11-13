import difflib
import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    action: str
    requester: str
    diff: str
    summary: str
    diff_hash: str


@dataclass(frozen=True)
class Decision:
    approved: bool
    reviewer: str
    reason: str
    seen_hash: str


def make_request(old: str, new: str, action: str, requester: str) -> Request:
    lines = list(
        difflib.unified_diff(old.splitlines(), new.splitlines(), "current", "proposed", lineterm="")
    )
    added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
    diff = "\n".join(lines)
    return Request(
        action,
        requester,
        diff,
        f"+{added} -{removed} lines",
        hashlib.sha256(diff.encode()).hexdigest(),
    )


def accept(request: Request, decision: Decision) -> str | None:
    if decision.reviewer == request.requester:
        return "reviewer must not be the requester"
    if not decision.approved:
        return None
    if len(decision.reason.split()) < 3:
        return "approval needs a reason of at least three words"
    if decision.seen_hash != request.diff_hash:
        return "approved diff does not match the current request"
    return None
