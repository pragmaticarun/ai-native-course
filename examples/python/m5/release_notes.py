"""M5 worked example: a release-notes agent with a meaningful approval gate.

planner -> workers draft sections -> human approves -> publish (mocked).

The approval gate is designed against "HITL theater" (rubber-stamp approvals):
* the human sees a DIFF against the last published notes, not just the new text;
* approving requires a written reason; empty or one-word reasons are rejected;
* nothing is published unless the decision object says approved=True;
* every decision is logged with the diff the human actually saw.
"""

from __future__ import annotations

import difflib
from collections.abc import Callable
from dataclasses import dataclass, field

from aincourse import AssistantTurn, Message, ScriptedModel


@dataclass(frozen=True)
class Decision:
    approved: bool
    reason: str
    reviewer: str


@dataclass
class Publisher:
    """The only component with the 'write' permission. Mocked: it records, never sends."""

    published: list[str] = field(default_factory=list)

    def publish(self, notes: str) -> str:
        self.published.append(notes)
        return f"published v{len(self.published)}"


@dataclass
class AuditLog:
    entries: list[dict] = field(default_factory=list)


def plan_sections(commits: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"Features": [], "Fixes": [], "Other": []}
    for c in commits:
        kind = c.split(":", 1)[0]
        sections["Features" if kind == "feat" else "Fixes" if kind == "fix" else "Other"].append(
            c.split(":", 1)[-1].strip()
        )
    return {k: v for k, v in sections.items() if v}


def draft_section(title: str, items: list[str]) -> str:
    worker = ScriptedModel(
        lambda msgs, tools: AssistantTurn(text="\n".join(f"- {i[0].upper()}{i[1:]}" for i in items))
    )
    body = worker.complete(
        [Message("system", f"Write the {title} section."), Message("user", "\n".join(items))]
    ).text
    return f"## {title}\n{body}"


def review_request(previous: str, draft: str) -> str:
    diff = difflib.unified_diff(
        previous.splitlines(), draft.splitlines(), "published", "draft", lineterm=""
    )
    return "\n".join(diff)


def validate_decision(d: Decision) -> str | None:
    if d.approved and len(d.reason.split()) < 3:
        return "approval needs a reason of at least three words"
    if not d.reviewer:
        return "decision must name a reviewer"
    return None


def run(
    commits: list[str],
    previous: str,
    human: Callable[[str], Decision],
    publisher: Publisher,
    log: AuditLog,
) -> str:
    draft = "\n\n".join(draft_section(t, items) for t, items in plan_sections(commits).items())
    diff = review_request(previous, draft)
    decision = human(diff)
    problem = validate_decision(decision)
    log.entries.append({"diff": diff, "decision": decision, "problem": problem})
    if problem:
        return f"blocked: {problem}"
    if not decision.approved:
        return f"rejected: {decision.reason}"
    return publisher.publish(draft)


if __name__ == "__main__":
    commits = ["feat: add AV1 decode", "fix: crash on empty playlist", "chore: bump deps"]
    pub, log = Publisher(), AuditLog()

    def human(diff: str) -> Decision:
        print(diff)
        return Decision(True, "Checked against the merged PR list", "arun")

    print(run(commits, "## Features\n- Old thing", human, pub, log))
