"""P2 evals: graph shape, retries, critic, HITL, tracing and the eval suite.

PROJECT_VARIANT=starter|solution pytest projects/p2/evals
"""

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from p2_critic import critique, supported
from p2_evals import (
    citation_precision,
    gold_recall,
    run_question,
    run_suite,
    summary,
    trajectory_ok,
)
from p2_graph import build
from p2_kit import QUESTIONS, MockLLM, Search, TransientSearchError
from p2_tracing import memory_tracer

Q = {q["id"]: q for q in QUESTIONS}


def run_to_gate(graph, question, tid="t"):
    cfg = {"configurable": {"thread_id": tid}}
    steps = [
        k for ev in graph.stream({"question": question}, cfg, stream_mode="updates") for k in ev
    ]
    return cfg, steps


# ------------------------------------------------------------------ M1 supervisor + fan-out
def test_supervisor_fans_out_one_worker_per_topic():
    _, steps = run_to_gate(build(MockLLM(), Search()), Q["q1"]["question"])
    assert steps[0] == "supervisor" and steps.count("research") == 2
    assert steps.index("write") > max(i for i, s in enumerate(steps) if s == "research")


def test_out_of_scope_question_is_not_answered():
    g = build(MockLLM(), Search())
    cfg, steps = run_to_gate(g, Q["q5"]["question"])
    assert steps == ["supervisor", "no_evidence"]
    assert g.get_state(cfg).values["report"].startswith("No sources")


# ------------------------------------------------------------------ M2 workers: retries, sources
def test_transient_search_errors_are_retried():
    s = Search(fail_first=2)
    cfg, steps = run_to_gate(build(MockLLM(), s), Q["q2"]["question"])
    assert "__interrupt__" in steps and len(s.calls) >= 3


def test_retries_give_up_eventually():
    with pytest.raises(TransientSearchError):
        run_to_gate(build(MockLLM(), Search(fail_first=5)), Q["q2"]["question"])


def test_outdated_sources_are_dropped_and_claims_merged():
    g = build(MockLLM(), Search())
    cfg, _ = run_to_gate(g, Q["q1"]["question"])
    cites = {c["doc"] for f in g.get_state(cfg).values["findings"] for c in f["claims"]}
    assert "bus-old" not in cites and {"bus-2025", "bus-fares"} <= cites
    cfg, _ = run_to_gate(g, Q["q3"]["question"], "t3")
    texts = [d["text"] for d in g.get_state(cfg).values["draft"]]
    assert len(texts) == len(set(texts))  # tram and budget workers found the same sentence


# ------------------------------------------------------------------ M3 critic
def test_critic_rules():
    good = "Cycling grew 18 percent compared with 2024."
    assert supported(good, "cycling-2025")
    assert not supported(good.replace("18", "22"), "cycling-2025")  # changed number
    assert not supported(good, "bus-2025")  # wrong citation
    draft = [{"text": good, "cite": "cycling-2025"}, {"text": good, "cite": ""}]
    subqs = [{"topic": "cycling", "q": "c?"}, {"topic": "tram", "q": "t?"}]
    c = critique(
        draft, subqs, [{"topic": "cycling", "claims": [1]}, {"topic": "tram", "claims": []}]
    )  # noqa: E501
    assert c.bad == [1] and c.uncovered == ["t?"] and not c.ok


def test_reflection_fixes_a_sloppy_first_draft():
    llm = MockLLM(sloppy="first")
    g = build(llm, Search())
    cfg, steps = run_to_gate(g, Q["q1"]["question"])
    v = g.get_state(cfg).values
    assert steps.count("write") == 2 and v["revisions"] == 1 and llm.drafts == 2
    assert citation_precision(v["draft"]) == 1.0 and v["bad"] == []


def test_revision_cap_hands_problems_to_the_human():
    g = build(MockLLM(sloppy="always"), Search(), max_revisions=2)
    cfg, steps = run_to_gate(g, Q["q1"]["question"])
    assert steps.count("write") == 3 and steps[-1] == "__interrupt__"
    payload = g.get_state(cfg).tasks[0].interrupts[0].value
    assert payload["revisions"] == 2 and payload["notes"] and "Reviewer notes" in payload["report"]


# ------------------------------------------------------------------ M4 human in the loop
@pytest.mark.parametrize(
    "answer,decision,published",
    [
        ("approve", "approved", True),
        ("reject", "rejected", None),
        ({"edit": "Short."}, "edited", True),
    ],
)
def test_human_gate(answer, decision, published):
    g = build(MockLLM(), Search())
    cfg, _ = run_to_gate(g, Q["q2"]["question"])
    assert not g.get_state(cfg).values.get("published")
    g.invoke(Command(resume=answer), cfg)
    v = g.get_state(cfg).values
    assert v["decision"] == decision and v.get("published") is published
    if decision == "edited":
        assert v["report"] == "Short."


def test_pause_survives_a_restart():
    saver = InMemorySaver()
    cfg, _ = run_to_gate(build(MockLLM(), Search(), checkpointer=saver), Q["q4"]["question"], "x")
    fresh = build(MockLLM(), Search(), checkpointer=saver)  # new process, same checkpoint store
    assert fresh.get_state(cfg).next == ("approve",)
    fresh.invoke(Command(resume="approve"), cfg)
    assert fresh.get_state(cfg).values["published"] is True


# ------------------------------------------------------------------ M5 tracing
def test_every_node_is_traced():
    tracer, exporter = memory_tracer()
    run_to_gate(build(MockLLM(), Search(), tracer=tracer), Q["q1"]["question"])
    spans = exporter.get_finished_spans()
    names = [s.name for s in spans]
    assert names.count("p2.research") == 2
    assert {"p2.supervisor", "p2.write", "p2.critic"} <= set(names)
    topics = {(s.attributes or {}).get("p2.topic") for s in spans if s.name == "p2.research"}
    assert topics == {"bus", "cycling"}


# ------------------------------------------------------------------ M6 evals
def test_trajectory_checker_catches_bad_runs():
    good = ["supervisor", "research", "research", "write", "critic", "__interrupt__"]
    assert trajectory_ok(good, ["a", "b"]) == []
    assert trajectory_ok(good, ["a"])  # wrong worker count
    assert trajectory_ok(["supervisor", "research", "write", "approve"], ["a"])  # skipped critic
    assert trajectory_ok(
        [
            "supervisor",
            "research",
            "write",
            "critic",
            "research",
            "write",
            "critic",
            "__interrupt__",
        ],
        ["a", "b"],
    )  # noqa: E501
    assert trajectory_ok(["supervisor", "no_evidence"], []) == []


def test_factuality_metrics():
    d = [{"text": "Cycling grew 18 percent compared with 2024.", "cite": "cycling-2025"},
         {"text": "Cycling grew 22 percent.", "cite": "cycling-2025"}]  # fmt: skip
    assert citation_precision(d) == 0.5
    assert gold_recall(d, [["18 percent", "cycling-2025"], ["3.1 million", "cycling-2025"]]) == 0.5


def test_suite_passes_and_parallelism_pays():
    rows = run_suite(sloppy="first")
    s = summary(rows)
    assert s["trajectory_pass"] == 1.0, [r.problems for r in rows]
    assert s["mean_gold_recall"] == 1.0 and s["mean_citation_precision"] == 1.0
    q1 = rows[0]
    assert q1.critical_path < q1.sim_seconds and q1.decision == "approved"


def test_rejected_report_is_not_published():
    r = run_question(Q["q2"], human="reject")
    assert r.decision == "rejected"
