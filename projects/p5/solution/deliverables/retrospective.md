# Retrospective: Larkspur Clips capstone

## What we changed

- AGENTS.md with a `Verify:` line and `./verify.sh`: one command for Python, TypeScript and
  Rust, no network, a couple of seconds.
- Tests in all three languages. The Rust tests were behind `--features full`, so plain
  `cargo test` ran none of them; the gate is gone. The slow "staging" test is marked `slow`
  and skipped by default instead of costing two seconds on every run.
- CI on every PR, a PR template, CODEOWNERS and a review policy (400 lines, provenance,
  the prompter can't be the only approver, two approvals for `.github/` and `rust/`).
- A first spec in Spec Kit format and a `run-verify` skill.

## What the numbers say

- The mock agent solved 3 of 10 seeded tasks before and 10 of 10 after; rework fell from 70%
  to 0%. Before, the agent found no documented check, guessed `pytest`, and that only ran a
  Python file covering one function, so 7 wrong fixes "passed".
- The agent ran its check 11 times before and 18 times after: better checks reject wrong
  candidates, so it tries more of them. That's the point, not a cost to hide.
- Review time is a course proxy (base + per line + a penalty when there's no trusted check),
  not a measurement of people.

## What didn't work

- The capability scores are still the team's own judgement; nothing here measures them.
- The bench uses a scripted agent with fixed candidate patches. A real agent would write
  different wrong fixes; the seeded tasks only test what the hidden acceptance tests check.
- Healthy data ecosystems and quality internal platforms stayed at 1; L3 needs them.

## Next level

L3 still needs an eval suite in the repo, AI-accessible internal data and a quality internal
platform (see the gaps list in the assessment). Stage 3 of the adoption plan starts on that.
