# AGENTS.md — Larkspur Clips

Setup: `uv venv && uv pip install pytest` (Python 3.13), Node 24, Rust stable.
Verify: `./verify.sh`

`./verify.sh` is the one command that says "done": Python tests, TypeScript tests (Node's
test runner with type stripping) and the Rust crate's tests. It takes a few seconds, uses no
network and must pass before you open a PR.

## Layout
- `py/clipsvc/` Python service code; tests in `py/tests/` (`@pytest.mark.slow` tests are
  skipped by default; they need staging).
- `web/src/` TypeScript helpers; tests in `web/test/*.test.ts`.
- `rust/clipcore/` timecode core; tests in `rust/clipcore/tests/`.
- `specs/` one folder per feature (Spec Kit layout): read the spec before changing behaviour.
- `skills/` agent skills for repeated jobs.

## Rules
- Every behaviour change comes with a test in the same language.
- Keep PRs under 400 changed lines; follow `docs/REVIEW_POLICY.md`.
- Don't edit tests to make them pass; if a test is wrong, say so in the PR.
- Never paste customer data into prompts (`docs/AI_POLICY.md`).
