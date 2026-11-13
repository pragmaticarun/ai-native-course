"""M9 L9.4: client-side MCP security checks.

* Per-tool scopes: the host maps each tool to the OAuth scopes it needs and refuses a
  call whose token lacks them (defence in depth: the server must check too).
* Tool-definition pinning: hash every tool's name, description and schemas at review
  time; refuse to run if a definition changes later (a "rug pull").
* Poisoning scan: flag descriptions that carry instructions aimed at the model.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from typing import Any

POISON_PATTERNS = {
    "hidden-instruction": (
        r"ignore (all |any )?(previous|prior) instructions|<important>|system prompt"
    ),
    "secrecy": r"do not (tell|inform|mention)|without telling",
    "credential-path": r"~/\.ssh|id_rsa|\.aws/credentials|\.env\b",
    "exfiltration": r"https?://(?!localhost)[^\s]+\?(data|q|payload)=|send (it|them|the file) to",
    "cross-tool": r"before (using|calling) any other tool|instead of the \w+ tool",
}


def scan_description(text: str) -> list[str]:
    low = text.lower()
    return [name for name, pat in POISON_PATTERNS.items() if re.search(pat, low)]


def tool_fingerprint(tool: Any) -> str:
    body = {
        "name": tool.name,
        "description": tool.description or "",
        "input": tool.input_schema,
        "output": tool.output_schema,
    }
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def pin(tools: Iterable[Any]) -> dict[str, str]:
    return {t.name: tool_fingerprint(t) for t in tools}


def pin_drift(pinned: Mapping[str, str], tools: Iterable[Any]) -> dict[str, str]:
    """name -> 'changed' | 'added' | 'removed' for every difference from the pins."""
    now = pin(tools)
    drift = {n: "changed" for n in now.keys() & pinned.keys() if now[n] != pinned[n]}
    drift |= {n: "added" for n in now.keys() - pinned.keys()}
    drift |= {n: "removed" for n in pinned.keys() - now.keys()}
    return drift


class ScopeError(PermissionError):
    pass


def require_scopes(tool: str, granted: set[str], policy: Mapping[str, set[str]]) -> None:
    """Raise unless `granted` covers `policy[tool]`. Unknown tools are denied."""
    if tool not in policy:
        raise ScopeError(f"{tool}: no scope policy, denied by default")
    missing = policy[tool] - granted
    if missing:
        raise ScopeError(f"{tool}: missing scopes {sorted(missing)}")
