"""STARTER. TODO: trajectory checks and citation precision.

P2 milestone 6: the eval suite (trajectory, factuality, cost and latency).

* trajectory: supervisor first; one research worker per expected topic; every write is
  followed by a critic; revisions within the cap; the run ends at the human gate (or at
  no_evidence for out-of-scope questions);
* factuality: *gold recall* (each gold fact appears in a sentence citing the right
  document) and *citation precision* checked strictly and independently of the critic
  (the cited document must contain the sentence verbatim);
* cost/latency: model calls, tokens, simulated model seconds, the simulated critical path
  with parallel workers, and wall time.

Run: `uv run --project python python projects/p2/solution/p2_evals.py`
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from langgraph.types import Command  # noqa: E402
from p2_graph import build  # noqa: E402
from p2_kit import QUESTIONS, MockLLM, Search  # noqa: E402


def trajectory_ok(steps: list[str], topics: list[str], max_revisions: int = 2) -> list[str]:
    """Problems with a run's node sequence (empty list = OK)."""
    return []  # TODO: supervisor first, workers per topic, fan-in, critic after write, cap, gate


def gold_recall(draft: list[dict[str, str]], gold: list[list[str]]) -> float:
    if not gold:
        return 1.0
    hit = sum(any(g in d["text"] and d["cite"] == doc for d in draft) for g, doc in gold)
    return round(hit / len(gold), 3)


def citation_precision(draft: list[dict[str, str]]) -> float:
    if not draft:
        return 1.0
    return 1.0  # TODO: share of sentences found verbatim in the cited document


@dataclass
class Result:
    qid: str
    steps: list[str]
    problems: list[str]
    recall: float
    precision: float
    revisions: int
    decision: str
    calls: int
    tokens: int
    sim_seconds: float
    critical_path: float
    wall_seconds: float


def run_question(q: dict[str, Any], sloppy: str = "first", fail_first: int = 1,
                 human: Any = "approve") -> Result:  # fmt: skip
    llm = MockLLM(sloppy=sloppy)
    graph = build(llm, Search(fail_first=fail_first))
    cfg = {"configurable": {"thread_id": q["id"]}}
    t0 = time.perf_counter()
    steps: list[str] = []
    for ev in graph.stream({"question": q["question"]}, cfg, stream_mode="updates"):
        steps += list(ev)
    trajectory = steps.copy()
    if graph.get_state(cfg).next:
        for ev in graph.stream(Command(resume=human), cfg, stream_mode="updates"):
            steps += list(ev)
    v = graph.get_state(cfg).values
    draft = v.get("draft", [])
    return Result(q["id"], steps, trajectory_ok(trajectory, q["topics"]),
                  gold_recall(draft, q["gold"]), citation_precision(draft),
                  v.get("revisions", 0), v.get("decision", "none"), llm.usage.calls,
                  llm.usage.tokens_in + llm.usage.tokens_out, round(llm.usage.sim_seconds, 2),
                  llm.usage.critical_path(), round(time.perf_counter() - t0, 3))  # fmt: skip


def run_suite(sloppy: str = "first") -> list[Result]:
    return [run_question(q, sloppy) for q in QUESTIONS]


def summary(rows: list[Result]) -> dict[str, float]:
    n = len(rows)
    return {
        "questions": n,
        "trajectory_pass": sum(not r.problems for r in rows) / n,
        "mean_gold_recall": round(sum(r.recall for r in rows) / n, 3),
        "mean_citation_precision": round(sum(r.precision for r in rows) / n, 3),
        "tokens": sum(r.tokens for r in rows),
        "sim_seconds_sequential": round(sum(r.sim_seconds for r in rows), 2),
        "sim_seconds_critical_path": round(sum(r.critical_path for r in rows), 2),
    }


def table(rows: list[Result]) -> str:
    head = ("| question | trajectory | gold recall | citation precision | revisions | calls | "
            "tokens | sim s (sequential) | sim s (critical path) |\n|---|---|---|---|---|---|---|---|---|")  # fmt: skip # noqa: E501
    body = "\n".join(
        f"| {r.qid} | {'ok' if not r.problems else '; '.join(r.problems)} | {r.recall} | "
        f"{r.precision} | {r.revisions} | {r.calls} | {r.tokens} | {r.sim_seconds} | "
        f"{r.critical_path} |"
        for r in rows
    )
    return f"{head}\n{body}"


if __name__ == "__main__":
    rs = run_suite()
    print(table(rs))
    print(summary(rs))
