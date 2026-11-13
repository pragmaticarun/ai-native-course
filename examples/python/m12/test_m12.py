from __future__ import annotations

import governance
import journey
import ladder
import plan90


def test_ladder_cites_six_levels_and_seven_capabilities():
    assert sorted(ladder.SHAPIRO) == [0, 1, 2, 3, 4, 5]
    assert len(ladder.DORA_AI_CAPABILITIES) == 7
    for need in ladder.ENTRY.values():  # every entry capability is one of DORA's seven
        assert set(need["capabilities"]) <= set(ladder.DORA_AI_CAPABILITIES)
    assert ladder.__doc__ and "SYNTHESIS" in ladder.__doc__


def test_skipping_levels_accumulates_gaps():
    t = ladder.Team(
        "x", level=1, capabilities={"clear and communicated AI stance"}, artifacts={"ai-policy"}
    )
    g = ladder.gaps(t, 3)
    assert "L2 artifact: agents-md" in g and "L3 artifact: eval-suite" in g
    assert ladder.gaps(t, 5)[-1] == "L5: not a target in this course"


def test_review_load():
    assert (
        ladder.review_load(ladder.Team("x", 2, reviewer_hours_per_week=10, agent_prs_per_week=30))
        == 1.5
    )
    assert ladder.review_load(ladder.Team("y", 2, agent_prs_per_week=1)) == float("inf")


def test_journey_replay():
    r = journey.replay()
    assert [(w, ok) for w, _, _, ok, _ in r] == [
        ("W01", False),
        ("W04", True),
        ("W09", False),
        ("W12", True),
    ]
    w01 = r[0][4]
    assert any("review load 1.25" in p for p in w01) and any("agents-md" in p for p in w01)
    assert r[2][4] == ["L3 capability: quality internal platforms", "L3 artifact: eval-suite"]


def test_journey_artifacts_exist():
    for name in ("AGENTS.md", "pr-policy.yaml", "plan.yaml", "quarter.yaml"):
        assert (journey.FIXTURES / name).is_file()


def test_governance_policy_and_audit():
    p = governance.Policy(
        {
            "coding-agent": governance.ToolGrant(
                "coding-agent", "internal", {"edit", "run-tests", "push"}, {"push"}
            ),
            "chat": governance.ToolGrant("chat", "public", {"ask"}),
        }
    )
    assert p.check("coding-agent", "edit", "internal") == "allow"
    assert p.check("coding-agent", "push", "internal").startswith("ask")
    assert p.check("coding-agent", "edit", "confidential").startswith("deny: confidential")
    assert p.check("chat", "ask", "internal").startswith("deny")
    assert p.check("browser-agent", "click", "public").startswith("deny: browser-agent is not")
    log = governance.AuditLog()
    for a in ("edit", "run-tests", "push"):
        log.append("agent:42", "coding-agent", a, p.check("coding-agent", a, "internal"))
    assert log.verify()
    log.entries[1]["decision"] = "allow (edited)"
    assert not log.verify()
    log2 = governance.AuditLog()
    for a in ("edit", "push"):
        log2.append("agent:42", "coding-agent", a, "allow")
    del log2.entries[0]
    assert not log2.verify()


def test_plan_template():
    assert plan90.check_plan(plan90.load((journey.FIXTURES / "plan.yaml").read_text())) == []
    bad = plan90.load(
        """
start: 2026-01-05
stages:
  - name: go fast
    ends: 2026-06-01
    metrics: [{name: "% of code written by AI", baseline: 10%, target: 60%}]
"""
    )
    probs = plan90.check_plan(bad)
    assert "stage 1 (go fast): no exit criterion" in probs
    assert "stage 1 (go fast): no guardrail metric" in probs
    assert any("vanity" in p for p in probs) and any("> 90" in p for p in probs)
