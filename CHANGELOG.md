# Changelog

All notable changes to the course. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-11-13

### Content
- Modules **M4–M6** built: 26 lessons (M4 context engineering & memory: 7; M5 planning, reflection, multi-agent, HITL: 9; M6 evals, guardrails, observability, cost/latency: 10), worked examples in Python and TypeScript (mock models only), 9 exercises with CI-checked solutions (solution passes, starter fails), 3 quizzes (23 questions).
- M6 **GUI-agent eval harness** (`examples/python/m6/gui_eval_harness.py`): 15 tasks on the M3 simulator, setup → run → state check → teardown, pass@k (unbiased estimator, Chen et al. 2021), unsafe-action counting, and an optional guard from M5.
- M2 **Kotlin Multiplatform** example is now real code: `kmp/shared` (`commonMain` event extractor with JSON repair and BUSY back-off, fakes for LiteRT-LM and Gemini Nano), plus KMP pieces for M4 (small-window history fitting) and M5 (confirmation guard for destructive tools). 12 `jvmTest` tests.
- Site: `Exercise` component takes an optional `file` prop (for TS exercises); M4–M6 sidebar groups.

### CI
- New `kmp` job: Temurin 21 (`actions/setup-java@v6`), `gradle/actions/setup-gradle@v6`, runs `./gradlew :shared:jvmTest`.

### Dependency pins (new)
- Python: `langgraph 1.2.21`, `inspect-ai 0.3.289`, `opentelemetry-sdk 1.45.2`.
- Kotlin/Gradle: Kotlin `2.4.21`, Gradle wrapper `9.9.1`, JDK 21 (Temurin), `kotlinx-coroutines 1.11.0`, `kotlinx-serialization-json 1.13.0` (not in the syllabus pin table; added for the M2 JSON parsing).

### Known gaps / untested
- KMP: only the **JVM** target is built and tested. The Android target is not configured (no Android SDK on the build box or in CI), and nothing ran on the Galaxy A73 or an emulator. ML Kit GenAI concepts are mirrored with course-owned types, **not** the ML Kit API.
- On-device eval numbers (`examples/python/m6/fixtures/ondevice_runs.json`) are a **synthetic** fixture with placeholder model names, not measurements.
- GUI-agent evals run against the M3 simulator only; no real device, emulator, or browser.
- promptfoo, DeepEval, Logfire and OTLP export are described but **not exercised**; tracing is tested with the OpenTelemetry in-memory exporter only. Inspect AI runs offline with its mock model.
- Prices in cost examples are illustrative, not current provider prices.
- Live-provider paths are still not exercised in CI.

## [0.1.0] - 2026-11-13

### Content
- Modules **M0–M3** built: 19 lessons, worked examples in Python and TypeScript, 11 exercises with CI-tested solutions, 4 quizzes (29 questions).
- Syllabus v0.3 published as the [syllabus page](https://pragmaticarun.github.io/ai-native-course/syllabus/).

### Dependency pins
- Python 3.13: `pydantic 2.14.3`, `pydantic-ai-slim 2.68.0`, `pyyaml 6.0.3`; dev: `pytest 9.2.0`, `ruff 0.17.5`, `mypy 2.4.1`.
- TypeScript: `ai 7.0.170` (syllabus planned 7.0.172; it was published less than 24 h before this release and pnpm 12's default minimum-release-age policy rejects it, so we pinned the previous release), `zod 4.6.7`, `typescript 7.0.2`, `vitest 5.1.0`.
- Site: `astro 7.4.11`, `@astrojs/starlight 0.42.11`, `starlight-links-validator 0.27.0`.

### Known gaps
- Device/emulator steps (adb mobile-use, Android/KMP) are marked **untested**; only their parsing logic runs in CI.
- Live-provider (`--live`) paths are not exercised in CI (no API keys stored).
