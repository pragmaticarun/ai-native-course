# Instructions for coding agents working on this repo

- Every code sample shown on the site must live under `examples/` or `exercises/` and be tested. Pages
  embed code with `<Snippet path=...>` / `<Exercise dir=...>`, which read the tested file (the build fails if it's missing).
- Default to mock models. Never add tests that need network or API keys.
- Exercises: the solution must pass and the starter must fail (`scripts/check_exercises.py`).
- Never invent frameworks, levels, statistics, APIs or versions. Link primary sources; label anything unverified.
- Mark device/emulator steps as **untested** unless they were actually run.
- Before pushing: Python lint/type/tests, `pnpm typecheck && pnpm test`, quiz validation, `cd site && pnpm build`.
