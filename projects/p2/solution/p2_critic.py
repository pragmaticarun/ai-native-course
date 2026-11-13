"""P2 milestone 3: the critic (reflection with checkable rules).

A cited sentence is *supported* when the cited document exists, every number in the
sentence appears in that document, and most of its content words do too. The critic
returns the indices of unsupported sentences and the sub-questions with no supported
sentence, so the writer gets specific feedback rather than "try again".

Rules like these catch changed numbers and wrong citations; they can't judge a subtle
paraphrase. For that you'd add an LLM judge, calibrated against these rules (M6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from p2_kit import DOCS, numbers, words


def supported(text: str, doc_id: str, min_overlap: float = 0.7) -> bool:
    doc = DOCS.get(doc_id)
    if doc is None:
        return False
    body = doc["text"]
    if any(n not in numbers(body) for n in numbers(text)):
        return False
    claim = set(words(text))
    if not claim:
        return False
    return len(claim & set(words(body))) / len(claim) >= min_overlap


@dataclass
class Critique:
    bad: list[int] = field(default_factory=list)
    uncovered: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.bad


def critique(draft: list[dict[str, str]], subqs: list[dict[str, str]],
             findings: list[dict[str, Any]]) -> Critique:  # fmt: skip
    c = Critique()
    for i, s in enumerate(draft):
        if not s.get("cite"):
            c.bad.append(i)
            c.notes.append(f"sentence {i} has no citation")
        elif not supported(s["text"], s["cite"]):
            c.bad.append(i)
            c.notes.append(f"sentence {i} is not supported by [{s['cite']}]")
    topics_with_text = {f["topic"] for f in findings if f["claims"]}
    for sq in subqs:
        if sq["topic"] not in topics_with_text:
            c.uncovered.append(sq["q"])
            c.notes.append(f"no evidence found for: {sq['q']}")
    return c
