# Instructions for coding agents working on this repo

- Every code sample shown on the site must live under `examples/` or `exercises/` and be tested. Pages
  embed code with `<Snippet path=...>` / `<Exercise dir=...>`, which read the tested file (the build fails if it's missing).
- Default to mock models. Never add tests that need API keys or call model providers. The one network
  exception: Temporal tests (M8) let the Temporal SDKs download their test/dev server binaries.
- Exercises: the solution must pass and the starter must fail (`scripts/check_exercises.py`).
- Never invent frameworks, levels, statistics, APIs or versions. Link primary sources; label anything unverified.
- Mark device/emulator steps as **untested** unless they were actually run.
- Before pushing: Python lint/type/tests, `pnpm typecheck && pnpm test`, quiz validation, `cargo fmt --check && cargo clippy -- -D warnings && cargo test` in `rust/media-probe`, `./gradlew :shared:jvmTest` in `kmp`, `cd site && pnpm build`.
- Do not install the Android SDK or accept its license without the owner's explicit approval.
