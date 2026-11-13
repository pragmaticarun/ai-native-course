"""L6.4: guardrails. Validate in, validate out, constrain tools, protect PII.

None of these make an agent safe alone. Pattern-based injection detection in
particular is easy to evade; the structural defences (least-privilege tools,
per-task allow-lists, human checkpoints, treating tool output as data) matter more.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MAX_INPUT_CHARS = 8_000
INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|messages)",
    r"disregard (the )?(system|developer) (prompt|message)",
    r"you are now (in )?\w+ mode",
    r"reveal (your )?(system prompt|instructions|secrets?)",
]
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d -]{8,}\d)(?!\d)")
CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
SECRET = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16})\b")


def check_input(text: str) -> list[str]:
    problems = []
    if len(text) > MAX_INPUT_CHARS:
        problems.append("input too long")
    for p in INJECTION_PATTERNS:
        if re.search(p, text, re.I):
            problems.append(f"possible prompt injection: /{p}/")
    return problems


def luhn_ok(number: str) -> bool:
    digits = [int(d) for d in number if d.isdigit()][::-1]
    total = sum(
        d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2) for i, d in enumerate(digits)
    )
    return total % 10 == 0


def redact_pii(text: str) -> str:
    text = CARD.sub(lambda m: "[CARD]" if luhn_ok(m.group(0)) else m.group(0), text)
    text = EMAIL.sub("[EMAIL]", text)
    return PHONE.sub("[PHONE]", text)


def check_output(text: str) -> list[str]:
    return ["output contains something that looks like a secret"] if SECRET.search(text) else []


@dataclass
class ToolPolicy:
    """Per-task allow-list plus argument constraints, checked before any tool runs."""

    allowed: set[str]
    arg_rules: dict[str, dict[str, re.Pattern]] = field(default_factory=dict)

    def check(self, tool: str, args: dict) -> str | None:
        if tool not in self.allowed:
            return f"tool {tool!r} not allowed for this task"
        for arg, pattern in self.arg_rules.get(tool, {}).items():
            if not pattern.fullmatch(str(args.get(arg, ""))):
                return f"{tool}.{arg}={args.get(arg)!r} violates policy"
        return None
