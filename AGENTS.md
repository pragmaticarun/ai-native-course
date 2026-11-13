# Instructions for coding agents working on this repo

Setup: `./verify.sh setup`
Verify: `./verify.sh`

- `./verify.sh python|ts|exercises|rust|kmp|site` runs one part. Nested AGENTS.md files in `kmp/`,
  `rust/` and `site/` add what's specific there.
- Every code sample shown on the site must live under `examples/` or `exercises/` and be tested. Pages
  embed code with `<Snippet path=...>` / `<Exercise dir=...>`, which read the tested file (the build fails if it's missing).
- Default to mock models. Never add tests that need API keys or call model providers. Network exceptions:
  Temporal tests (M8) let the Temporal SDKs download their test/dev server binaries, and the CI `speckit`
  job installs Spec Kit from GitHub.
- Exercises: the solution must pass and the starter must fail (`scripts/check_exercises.py`).
- Never invent frameworks, levels, statistics, APIs or versions. Link primary sources; label anything unverified.
- Mark device/emulator steps and anything not actually run as **untested**.
- Do not install the Android SDK or accept its license without the owner's explicit approval.
- Skills for recurring jobs live in `.claude/skills/` (Agent Skills format); Cursor rules in `.cursor/rules/`.
