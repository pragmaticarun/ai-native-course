# P5 — Capstone: move a small team repo up one maturity level

**After:** M10–M12 · **Languages:** the team repo is Python + TypeScript + Rust; the
assessment code is Python · mock coding agent, no API key

`common/legacy_repo/` is "Larkspur Clips" (fictional): a Python service, a TypeScript helper
and a Rust crate at roughly Shapiro L1. The README says `make test` (there's no Makefile),
the only Python test file covers one function and sleeps two seconds, the TypeScript code
has no tests, and the Rust tests only compile with `--features full`.

You assess it, change it, and measure the change with a mock agent on **ten seeded tasks**
(four Python, three TypeScript, three Rust) judged by hidden acceptance tests.

## Milestones

| # | Where | You build | Evals |
|---|---|---|---|
| M1 | `p5_assess.py` | detect the M12 ladder's artefacts from files; combine with the team's M1 worksheet | `test_legacy_repo_is_L1_*` |
| M2 | `overlay/` | agent-friendly repo: AGENTS.md with `Verify:`, `verify.sh`, fast tests in all three languages, CI | `test_repo_changes_meet_L2_*`, `test_no_existing_assertion_*` |
| M3 | `overlay/` | spec-driven flow (a Spec Kit spec that lints clean, a skill) and a PR pipeline (template, CODEOWNERS, review policy) | `test_repo_changes_meet_L2_*` |
| M4 | (provided bench) | measure before/after: success, rework, verify runs, review-time proxy | `test_agent_success_and_rework_*` |
| M5 | `deliverables/` | assessment report, adoption plan, dashboard (generated and committed), retrospective | `test_generated_reports_*`, `test_adoption_plan_*`, `test_retrospective_*` |

`overlay/` is copied over the legacy repo; it *is* your repo change, kept as files so the
evals can rebuild before and after from scratch.

## Done when

All evals pass with `PROJECT_VARIANT=solution P5_REQUIRE_ALL=1` (needs Node ≥ 22.6 and cargo).

## Stretch (not built here)

Point the bench at a live coding agent; add an eval suite to the team repo (L3); real DORA
metrics from the repo's history (M11's `dora.py`).
