# Instructions for coding agents working on this repo

Setup: `./verify.sh setup`
Verify: `./verify.sh`

- `./verify.sh python|ts|exercises|rust|kmp|site` runs one part. Nested AGENTS.md files in `kmp/`,
  `rust/` and `site/` add what's specific there.
- Every code sample shown on the site must live under `examples/` or `exercises/` and be tested. Pages
  embed code with `<Snippet path=...>` / `<Exercise dir=...>`, which read the tested file (the build fails if it's missing).
- Default to mock models. Never add tests that need API keys or call model providers. Network exceptions:
  Temporal tests (M8) let the Temporal SDKs download their test/dev server binaries, the CI `speckit`
  job installs Spec Kit from GitHub, the CI `llamacpp` job downloads a pinned llama.cpp build and model,
  and the CI `python` job installs browser-use 1.0.8 from PyPI into an isolated env for
  `examples/python/m15/test_browser_use_pins.py` (no Agent is built, no model is called).
- Exercises: the solution must pass and the starter must fail (`scripts/check_exercises.py`).
- New dependencies need the owner's OK: exact `==` pins, update `python/uv.lock` / `pnpm-lock.yaml`
  (hashes included), and respect the 1-day cooldown (`exclude-newer`, `minimumReleaseAge`). See M12 L12.3.
- Never invent frameworks, levels, statistics, APIs or versions. Link primary sources; label anything unverified.
- Mark device/emulator steps and anything not actually run as **untested**.
- Android SDK: the owner approved accepting its license and installing it on the box and in CI (14 Nov 2026).
  Pin SDK packages in CI; instrumentation tests are compiled only until a device run exists (mark them untested).
- Skills for recurring jobs live in `.claude/skills/` (Agent Skills format); Cursor rules in `.cursor/rules/`.
