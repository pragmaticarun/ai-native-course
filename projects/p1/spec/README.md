# P1 — Mini-SWE: issue → plan → edit → test → PR

**After:** M3–M6, M10–M11 · **Time:** ~10 hours · **Language:** Python (mock model; no API key)

Build a coding agent that takes an issue, writes a plan, edits files with read/write/search
tools in a git worktree, runs the tests, iterates, and opens a pull request with a summary and
a test report, or escalates honestly when it can't fix the bug.

Everything runs locally: the "repo" is a git clone of `common/fixture_repo` (a small library
called `textkit`), the "remote" is a bare git repo, and the "forge" that takes PRs is a JSON
file (`common/p1_kit.py: LocalForge`). **No GitHub repo is created or touched.**

## Milestones

| # | File | You build | Evals |
|---|---|---|---|
| M1 | `p1_context.py` | a repo map within a character budget | `test_repo_map_*`, `test_called_names_and_locate` |
| M2 | `p1_tools.py` | guarded tools: path allowlist, read-only tests, hidden `.git`, no options to pytest, scrubbed env + no network, truncation | `test_guardrails_refuse`, `test_symlink_*`, `test_tests_run_without_network`, `test_output_*` |
| M3 | `p1_repairer.py` | the scripted model: reproduce → localise → mutation search → finish or give up | `test_mutants_*`, benchmark |
| M4 | `p1_agent.py` | the loop: test-run/step/token budget, and a verified finish | `test_budget_*`, `test_finish_is_verified_not_trusted` |
| M5 | `p1_pr.py` | commit, push to the local origin, PR body with plan, change, before/after tests, diff stat, cost | `test_issue_to_pr_on_local_forge`, `test_escalation_opens_no_pr` |
| M6 | `p1_bench.py` | the 15-seeded-bug benchmark (13 fixable by one edit, 2 that need new logic) | `test_benchmark_15_seeded_bugs` |

## Done when

- every eval passes against your code;
- the benchmark resolves all 13 fixable bugs, escalates the 2 others, and touches no test file;
- every PR body's test report was measured by the loop, not claimed by the model.

## Stretch (not built in this course)

- Swap the scripted model for an LLM through Pydantic AI, the Claude Agent SDK or the AI SDK
  (TypeScript) behind the same `Model` protocol, and compare resolve rate, cost and wrong fixes.
- Run it as a background agent from GitHub Actions against a **sandbox repo you create for
  it**: ask the repo owner first; this course does not create one.
- Real isolation: run `run_tests` in a container or network namespace instead of the
  `sitecustomize` socket guard.
