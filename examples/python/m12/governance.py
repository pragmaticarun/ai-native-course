"""M12 L12.3: team-scale AI governance as code — a tool allowlist with data classes, and
a tamper-evident audit log of agent actions.

The policy shape is this course's. It encodes the kinds of control the cloud adoption
frameworks from M1 ask for (governance, security and data controls); it is not taken
from any one of them.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

DATA_CLASSES = ("public", "internal", "confidential", "restricted")


@dataclass
class ToolGrant:
    tool: str
    max_data_class: str
    actions: set[str]
    needs_approval: set[str] = field(default_factory=set)


@dataclass
class Policy:
    grants: dict[str, ToolGrant]

    def check(self, tool: str, action: str, data_class: str) -> str:
        g = self.grants.get(tool)
        if g is None:
            return f"deny: {tool} is not on the allowlist"
        if action not in g.actions:
            return f"deny: {tool} may not {action}"
        if DATA_CLASSES.index(data_class) > DATA_CLASSES.index(g.max_data_class):
            return f"deny: {data_class} data may not go to {tool} (max {g.max_data_class})"
        if action in g.needs_approval:
            return "ask: human approval required"
        return "allow"


def _digest(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


@dataclass
class AuditLog:
    """Append-only, hash-chained: editing or deleting an entry breaks `verify()`.
    Tamper-evident, not tamper-proof: anyone who can rewrite the whole file can rebuild
    the chain, so copy the latest hash somewhere they can't write."""

    entries: list[dict] = field(default_factory=list)

    def append(self, actor: str, tool: str, action: str, decision: str) -> None:
        prev = self.entries[-1]["hash"] if self.entries else "0" * 64
        body = {"actor": actor, "tool": tool, "action": action, "decision": decision, "prev": prev}
        self.entries.append({**body, "hash": _digest(body)})

    def verify(self) -> bool:
        prev = "0" * 64
        for e in self.entries:
            body = {k: v for k, v in e.items() if k != "hash"}
            if body["prev"] != prev or _digest(body) != e["hash"]:
                return False
            prev = e["hash"]
        return True
