"""P2 kit (provided): a small *fictional* corpus, a keyword search tool that can be made
flaky, and a deterministic mock LLM with usage accounting.

The corpus is about an invented city, Riverton, and every number in it is made up for the
exercise. The mock LLM stands in for model calls (decompose, extract, write) so the graph,
the critic and the evals are testable offline; it can be told to be *sloppy* (change a
number, cite the wrong document) so the critic has real mistakes to catch.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CORPUS: list[dict[str, Any]] = json.loads((HERE / "corpus.json").read_text())
QUESTIONS: list[dict[str, Any]] = json.loads((HERE / "questions.json").read_text())
DOCS = {d["id"]: d for d in CORPUS}

TOPICS = {
    "bus": ("bus", "ridership"),
    "cycling": ("cycl", "bike"),
    "tram": ("tram",),
    "air": ("air quality", "nitrogen", "pollution"),
    "parking": ("parking",),
    "budget": ("budget", "cost"),
}
STOP = set("a an and the of in on to for by with was were is are it its that this what how why "
           "did does do from as at than more be has had during year".split())  # fmt: skip


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower()) if w not in STOP]


def numbers(text: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", text)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=\.)\s+", text) if s.strip()]


class TransientSearchError(RuntimeError):
    """A timeout or 503 from the search backend: worth retrying."""


@dataclass
class Search:
    """Keyword search over the corpus. `fail_first=n` makes the first n calls per query
    raise TransientSearchError, to exercise retries."""

    fail_first: int = 0
    calls: list[str] = field(default_factory=list)

    def __call__(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        self.calls.append(query)
        if self.calls.count(query) <= self.fail_first:
            raise TransientSearchError(f"search timed out: {query!r}")
        q = set(words(query))
        bags = {d["id"]: set(words(d["title"] + " " + d["text"])) for d in CORPUS}
        df = {w: sum(w in b for b in bags.values()) for w in q}
        # IDF weighting: a word every document contains ("riverton") counts for nothing.
        idf = {w: math.log(len(CORPUS) / df[w]) for w in q if df[w]}
        scored = [(sum(idf.get(w, 0.0) for w in q & b), i) for i, b in bags.items()]
        return [DOCS[i] for s, i in sorted(scored, key=lambda t: (-t[0], t[1])) if s > 0][:k]


@dataclass
class Usage:
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    sim_seconds: float = 0.0  # simulated model latency, not wall time
    log: list[tuple[str, float]] = field(default_factory=list)  # (label, simulated seconds)

    def add(self, prompt: str, output: str, label: str = "") -> float:
        t_in, t_out = max(1, len(prompt) // 4), max(1, len(output) // 4)
        secs = round(0.3 + t_out / 50, 3)
        self.calls += 1
        self.tokens_in += t_in
        self.tokens_out += t_out
        self.sim_seconds += secs
        self.log.append((label, secs))
        return secs

    def critical_path(self) -> float:
        """Simulated latency if parallel research workers really run in parallel:
        sequential calls add up; for research, only the slowest worker counts."""
        seq = sum(s for lab, s in self.log if not lab.startswith("research:"))
        per: dict[str, float] = {}
        for lab, s in self.log:
            if lab.startswith("research:"):
                per[lab] = per.get(lab, 0.0) + s
        return round(seq + max(per.values(), default=0.0), 3)


@dataclass
class MockLLM:
    """Deterministic stand-in for the model calls the graph makes.

    sloppy="first": the first draft changes one number and mis-cites one sentence;
    sloppy="always": every draft does (to test the revision cap); sloppy="": never.
    """

    sloppy: str = ""
    usage: Usage = field(default_factory=Usage)
    drafts: int = 0

    def decompose(self, question: str) -> list[dict[str, str]]:
        ql = question.lower()
        year = (re.findall(r"\b20\d\d\b", question) or [""])[0]
        subqs = [
            {"topic": t, "q": f"What happened to {t} in Riverton {year}".strip() + "?"}
            for t, keys in TOPICS.items()
            if any(k in ql for k in keys)
        ]
        self.usage.add(question, json.dumps(subqs), "supervisor")
        return subqs

    def extract(self, subq: dict[str, str], doc: dict[str, Any]) -> list[str]:
        keys = TOPICS[subq["topic"]]
        found = [s for s in sentences(doc["text"]) if any(k in s.lower() for k in keys)]
        self.usage.add(subq["q"] + doc["text"], " ".join(found), f"research:{subq['topic']}")
        return found

    def write(
        self, question: str, findings: list[dict[str, Any]], feedback: list[int] | None = None
    ) -> list[dict[str, str]]:
        self.drafts += 1
        draft = [
            {"text": c["text"], "cite": c["doc"]}
            for f in sorted(findings, key=lambda f: f["topic"])
            for c in f["claims"]
        ]
        careless = self.sloppy == "always" or (self.sloppy == "first" and self.drafts == 1)
        if careless and len(draft) >= 2:
            first = draft[0]["text"]
            n = numbers(first)
            if n:
                draft[0] = {**draft[0], "text": first.replace(n[0], str(int(float(n[0])) + 4), 1)}
            wrong = next(d for d in DOCS if d != draft[1]["cite"])
            draft[1] = {**draft[1], "cite": wrong}
        if feedback and not careless:
            draft = [d for d in draft if d["text"].strip()]
        self.usage.add(question + json.dumps(findings), json.dumps(draft), "write")
        return draft
