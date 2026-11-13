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
    # TODO: show a diff, not just the new text.
    return Request(action, requester, new, "", "")


def accept(request: Request, decision: Decision) -> str | None:
    # TODO: rubber stamps pass this check.
    return None
