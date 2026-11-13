"""P5 milestones 1, 4 and 5: assess a repo against the course ladder, and report.

* `artifacts(repo)` detects the team artefacts the M12 ladder asks for, from files alone.
* `team(worksheet, artifacts)` combines them with the team's M1 worksheet (capabilities are
  human judgements; the code doesn't pretend to measure them).
* `assessment(...)` writes the baseline report; `dashboard(before, after)` the metrics.

Reused: M10's structural audit and skills validator, Spec Kit lint, and M12's ladder
(`gaps`, `ready_for`, `review_load`). The ladder is the course's synthesis of Shapiro's
levels and DORA's capabilities, not a published standard.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from ladder import DORA_AI_CAPABILITIES, SHAPIRO, Team, ready_for, review_load
from p5_kit import BenchResult
from repo_audit import audit, score
from skills import validate_skill
from speckit import lint_spec, parse_spec

# M1 worksheet keys, in the same order as M12's capability names.
M1_KEYS = (
    "clear_ai_stance",
    "healthy_data_ecosystems",
    "ai_accessible_internal_data",
    "strong_version_control",
    "small_batches",
    "user_centric_focus",
    "quality_internal_platforms",
)
FAST_TESTS_S = 30.0
REVIEW_BASE_MIN = 4.0  # course proxy, see review_minutes()


def _tests_for_every_language(repo: Path) -> bool:
    py = any((repo / "py" / "tests").glob("test_*.py"))
    ts = any((repo / "web" / "test").glob("*.test.ts"))
    rs_files = list((repo / "rust" / "clipcore" / "tests").glob("*.rs"))
    rs = any("cfg(feature" not in f.read_text() for f in rs_files)
    return py and ts and rs


def artifacts(repo: Path, verify_seconds: float | None = None) -> set[str]:
    """Artefact names from M12's ENTRY table that this repo has."""
    found: set[str] = set()
    checks = audit(repo)
    if (repo / "docs" / "AI_POLICY.md").is_file():
        found.add("ai-policy")
    if (repo / "AGENTS.md").is_file() and checks["verify-command"]:
        found.add("agents-md")
    if checks["verify-command"]:
        found.add("verify-command")
    if (
        _tests_for_every_language(repo)
        and verify_seconds is not None
        and verify_seconds <= FAST_TESTS_S
    ):
        found.add("fast-tests")
    if (repo / ".github" / "pull_request_template.md").is_file() and (
        repo / "docs" / "REVIEW_POLICY.md"
    ).is_file():
        found.add("pr-policy")
    specs = list(repo.glob("specs/*/spec.md"))
    if specs and all(not lint_spec(parse_spec(s.read_text())) for s in specs):
        found.add("specs")
    skill_dirs = [p.parent for p in repo.glob("skills/*/SKILL.md")]
    if skill_dirs and all(not validate_skill(d).errors for d in skill_dirs):
        found.add("skills")
    return found


def load_worksheet(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(path.read_text())
    return data


def team(ws: dict[str, Any], found: set[str]) -> Team:
    caps = {DORA_AI_CAPABILITIES[i] for i, k in enumerate(M1_KEYS) if ws["capabilities"][k] >= 2}
    return Team(
        name=ws["team"],
        level=ws["workflow_level"],
        capabilities=caps,
        artifacts=found,
        reviewer_hours_per_week=ws["reviewer_hours_per_week"],
        agent_prs_per_week=ws["agent_prs_per_week"],
        review_hours_per_pr=ws.get("review_hours_per_pr", 0.5),
    )


def review_minutes(pr_body: str, changed_lines: int) -> float:
    """Course proxy for reviewer time, NOT a measurement: a base cost, half a minute per
    changed line, and +10 minutes when the PR carries no passing check the reviewer can
    trust (they rerun or read everything)."""
    trusted = "./verify.sh` -> pass" in pr_body
    return REVIEW_BASE_MIN + 0.5 * changed_lines + (0.0 if trusted else 10.0)


def assessment(repo: Path, ws: dict[str, Any], before: BenchResult) -> str:
    found = artifacts(repo, before.verify_seconds if before.clean_verify_passes else None)
    t = team(ws, found)
    checks = audit(repo)
    ok2, problems2 = ready_for(t, ws["workflow_level"] + 1)
    lines = [
        f"# Baseline assessment: {ws['team']}",
        "",
        f"**Observed level:** L{t.level}. {SHAPIRO[t.level]}",
        "",
        "## Capabilities (team worksheet, 0-3)",
        "",
        "| capability | score |",
        "|---|---|",
        *[
            f"| {cap} | {ws['capabilities'][k]} |"
            for cap, k in zip(DORA_AI_CAPABILITIES, M1_KEYS, strict=True)
        ],
        "",
        f"## Repo audit (M10): {score(checks)}",
        "",
        *[f"- {'yes' if v else 'NO'}: {k}" for k, v in checks.items()],
        "",
        f"## Artefacts found: {', '.join(sorted(found)) or 'none'}",
        "",
        f"## Ready for L{t.level + 1}? {'yes' if ok2 else 'no'}",
        "",
        *[f"- {p}" for p in problems2],
        "",
        f"Review load if agents open {ws['agent_prs_per_week']} PRs/week: {review_load(t)} "
        "of reviewer time.",
        "",
        "## Agent baseline (10 seeded tasks, mock agent)",
        "",
        f"- verify command the agent found: `{' '.join(Path(x).name for x in before.verify_cmd)}`",
        f"- success {before.success_rate:.0%}, rework {before.rework_rate:.0%}",
        "",
        "Ladder = the course's synthesis (Shapiro levels + DORA capabilities), not a standard.",
    ]
    return "\n".join(lines) + "\n"


def dashboard(before: BenchResult, after: BenchResult) -> str:
    """Metrics that don't depend on machine speed (verify time is reported separately)."""

    def found(r: BenchResult) -> str:
        return "no" if r.verify_cmd[0].endswith("python") else "yes"

    def mean_review(r: BenchResult) -> float:
        return sum(review_minutes(t.pr_body, t.changed_lines) for t in r.tasks) / len(r.tasks)

    pct = "{:.0%}".format
    rows = [
        ("agent task success (10 seeded tasks)", pct(before.success_rate), pct(after.success_rate)),
        (
            "rework (passed own check, failed acceptance)",
            pct(before.rework_rate),
            pct(after.rework_rate),
        ),
        ("verify command found in AGENTS.md", found(before), found(after)),
        ("verify runs by the agent", str(before.verify_runs), str(after.verify_runs)),
        (
            "review time per PR (course proxy, min)",
            f"{mean_review(before):.1f}",
            f"{mean_review(after):.1f}",
        ),
    ]
    by_lang = {}
    for lang in ("py", "ts", "rs"):
        b = sum(t.solved for t in before.tasks if t.lang == lang)
        a = sum(t.solved for t in after.tasks if t.lang == lang)
        n = sum(t.lang == lang for t in before.tasks)
        by_lang[lang] = (b, a, n)
    out = ["# Metrics dashboard", "", "| metric | before | after |", "|---|---|---|"]
    out += [f"| {m} | {b} | {a} |" for m, b, a in rows]
    out += ["", "| language | before | after |", "|---|---|---|"]
    out += [f"| {lang} | {b}/{n} | {a}/{n} |" for lang, (b, a, n) in by_lang.items()]
    out += [
        "",
        "Mock agent and fixtures: these numbers show how to measure, not how a real "
        "agent or team would do.",
    ]
    return "\n".join(out) + "\n"


def retrospective_problems(text: str) -> list[str]:
    need = ("What we changed", "What the numbers say", "What didn't work", "Next level")
    probs = [f"missing section: {h}" for h in need if not re.search(rf"^## {h}", text, re.M)]
    if "TODO" in text:
        probs.append("TODO left in the retrospective")
    return probs


def write_reports(
    out: Path, repo_before: Path, ws: dict[str, Any], before: BenchResult, after: BenchResult
) -> None:
    """Regenerate the two generated deliverables (commit them; an eval checks they're current)."""
    (out / "assessment.md").write_text(assessment(repo_before, ws, before))
    (out / "dashboard.md").write_text(dashboard(before, after))
