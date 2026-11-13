"""P5 evals: baseline assessment, repo changes, before/after measurement and deliverables.

PROJECT_VARIANT=starter|solution pytest projects/p5/evals
The before/after bench needs Node >= 22.6 and cargo; P5_REQUIRE_ALL=1 makes their absence a
failure instead of a skip (the CI rust job sets it).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from ladder import gaps, ready_for
from p5_assess import (
    artifacts,
    assessment,
    dashboard,
    load_worksheet,
    retrospective_problems,
    team,
)
from p5_kit import HERE, LEGACY, bench, have_tools, make_repo
from plan90 import check_plan, load
from repo_audit import audit

VARIANT = os.environ.get("PROJECT_VARIANT", "solution")
PROJ = Path(__file__).resolve().parents[1] / VARIANT
OVERLAY, DELIV = PROJ / "overlay", PROJ / "deliverables"
WS_BEFORE = load_worksheet(HERE / "worksheet_before.yaml")


def need_tools() -> None:
    missing = [k for k, ok in have_tools().items() if not ok]
    if missing:
        if os.environ.get("P5_REQUIRE_ALL") == "1":
            pytest.fail(f"P5_REQUIRE_ALL=1 but missing: {missing}")
        pytest.skip(f"needs {missing} (Node >= 22.6, cargo)")


@pytest.fixture(scope="session")
def results(tmp_path_factory):
    need_tools()
    d = tmp_path_factory.mktemp("p5")
    return bench(d, "before"), bench(d, "after", OVERLAY), d


# ------------------------------------------------------------------ M1 baseline
def test_legacy_repo_is_L1_and_not_ready_for_L2(tmp_path):
    repo = make_repo(tmp_path / "legacy")
    found = artifacts(repo, None)
    assert found == {"ai-policy"}
    ok, problems = ready_for(team(WS_BEFORE, found), 2)
    assert not ok and "L2 artifact: agents-md" in problems and "L2 artifact: fast-tests" in problems
    assert sum(audit(repo).values()) == 1  # only "typed" (the Rust crate)


# ------------------------------------------------------------------ M2-M3 repo changes
def test_repo_changes_meet_L2_entry_and_start_L3(tmp_path):
    repo = make_repo(tmp_path / "after", OVERLAY)
    found = artifacts(repo, 5.0)
    assert {"agents-md", "verify-command", "fast-tests", "pr-policy", "specs", "skills"} <= found
    ws = load_worksheet(DELIV / "worksheet_after.yaml")
    t = team(ws, found)
    t.level = 1  # readiness is judged from where the team started
    assert ready_for(t, 2) == (True, [])
    assert "L3 artifact: pr-policy" not in gaps(t, 3)
    assert audit(repo)["ci"] and "./verify.sh" in (repo / ".github/workflows/ci.yml").read_text()


def test_no_existing_assertion_was_dropped():
    legacy = (LEGACY / "py/tests/test_durations.py").read_text()
    new = (OVERLAY / "py/tests/test_durations.py").read_text()
    for line in re.findall(r"assert .+", legacy):
        assert line in new, f"assertion removed: {line}"


# ------------------------------------------------------------------ M4 measure before/after
def test_agent_success_and_rework_before_and_after(results):
    before, after, _ = results
    assert before.success_rate <= 0.5 and before.rework_rate >= 0.5
    assert after.success_rate == 1.0 and after.rework_rate == 0.0
    assert after.clean_verify_passes and after.verify_seconds < 30
    assert after.verify_cmd == ["./verify.sh"]


# ------------------------------------------------------------------ M5 deliverables
def test_generated_reports_are_committed_and_current(results):
    before, after, d = results
    assert (DELIV / "assessment.md").read_text() == assessment(d / "before", WS_BEFORE, before)
    assert (DELIV / "dashboard.md").read_text() == dashboard(before, after)


def test_adoption_plan_passes_the_m12_checks():
    plan = load((DELIV / "adoption_plan.yaml").read_text())
    assert check_plan(plan) == []
    assert plan["stages"][0]["target_level"] == 2


def test_retrospective_is_complete():
    assert retrospective_problems((DELIV / "retrospective.md").read_text()) == []
