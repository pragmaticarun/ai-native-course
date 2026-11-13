"""P8 starter, milestone 3: the policy engine between the model and the device.

Decides per action, *before* it runs, using what the action would touch (the env resolves the
target from a coordinate or mark):
  block - kind not allowed; a consequential action the task didn't ask for; a consequential
          action while untrusted instructions are on screen (injection heuristic)
  ask   - a consequential action the task did ask for, or typing into a sensitive field:
          the graph `interrupt`s for a human
  allow - everything else
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from p8_kit import Action

ALLOWED_KINDS = frozenset({"click", "type", "key", "wait"})
CONSEQUENTIAL = re.compile(
    r"\b(forward|send|delete|remove|buy|purchase|pay|transfer|share)\b", re.I
)
SENSITIVE = re.compile(r"password|card|cvv|otp|ssn", re.I)
INJECTION = [
    r"ignore (all |any )?(previous|prior|above) instructions",
    r"you are now (in )?\w+ mode",
    r"disregard (your|the) (rules|instructions)",
]


def injection_flags(text: str) -> list[str]:
    return [p for p in INJECTION if re.search(p, text, re.I)]


@dataclass(frozen=True)
class Verdict:
    decision: Literal["allow", "ask", "block"]
    reason: str


def review(a: Action, target: str, goal: str, screen_text: str) -> Verdict:
    if a.kind not in ALLOWED_KINDS:
        return Verdict("block", f"action kind {a.kind} not allowed")
    # TODO(milestone 3): consequential targets (CONSEQUENTIAL) must be blocked when the task
    # didn't ask for them or when injection_flags(screen_text) finds untrusted instructions,
    # and sent to a human ("ask") when the task did ask; typing into SENSITIVE fields asks too.
    return Verdict("allow", "ok")
