# Changelog

All notable changes to the course. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] - 2026-11-13

### Content
- Modules **M7–M9** built: 17 lessons (M7 agent graphs & orchestration: 6; M8 durable execution & production: 5; M9 MCP servers & clients: 6) and 8 worked-example pages, with Python and TypeScript examples (mock models), 9 exercises with CI-checked solutions (solution passes, starter fails) and 3 quizzes (23 questions). New site groups: *Orchestration & Production* (M7–M8) and *AI-Native Development* (M9).
- M7: LangGraph (Python 1.2.21, LangGraph.js 1.7.3) examples for routing, `Send` fan-out with `max_concurrency`, subgraph supervisors (including the duplicated-reducer pitfall), `RetryPolicy`/timeouts/error handlers, a document-triage graph with an approval interrupt, the **computer-use loop as a graph** (observe → plan → guard → act → verify/recover, interrupt before consequential actions, retry on `act`, checkpoint/resume after a simulated emulator crash) and a **media fan-out graph** (4 scenes × 3 tasks, peak concurrency 3, partial failures).
- M8: Temporal in Python and TS. **Kill-the-worker** demo on the local Temporal dev server (worker subprocess SIGKILLed after step 6's side effect; resumes with 10 effects, 11 attempts). **Long media jobs**: chunked workflow with idempotent outputs, `.part` + rename, heartbeat resume mid-chunk; real ffmpeg on a generated clip. Pydantic AI on Temporal (`TemporalDurability`), approval signals that wait days (time-skipping server), `workflow.patched` versioning checked with the `Replayer`, idempotency/rate-limit/tenant budgets, SLO/burn-rate/release fingerprints.
- M9: media-probe MCP server in **Python** (`mcp` 2.3.0 `MCPServer`), **TypeScript** (`@modelcontextprotocol/server` 2.4.0, served with `serveStdio`) and **Rust** (`rmcp` 3.10.0, real ffprobe/ffmpeg), plus a **Kotlin** port (MCP Kotlin SDK 0.16.0 in KMP `commonMain`, JVM tests). A contract suite runs the Python client against the Python (in-process and stdio), TypeScript and Rust servers on **both** spec revisions (2026-07-28 and 2025-11-25); the TS client is also tested against the Rust binary. Confirmations via `input_required` / elicitation, caching hints, an agent using MCP tools, an **adb MCP server** tested over real Streamable HTTP on localhost (fake adb), tool pinning, poisoning scan and per-tool scopes.

### CI
- New `rust` job: Rust 1.100.0 (`rust-toolchain.toml`), `cargo fmt --check`, `cargo clippy -D warnings`, `cargo test`, then the cross-language MCP contract tests (Python and TypeScript clients against the Rust binary, real ffmpeg) with skips turned into failures (`MEDIA_PROBE_REQUIRE_ALL=1`).
- Temporal tests download Temporal's test server / CLI dev server binaries at test time (no account, no keys); `AGENTS.md` updated to allow that.

### Dependency pins (new)
- Python: `mcp 2.3.0`, `temporalio 1.36.0`.
- TypeScript: `@modelcontextprotocol/server 2.4.0`, `@modelcontextprotocol/client 2.4.0`, `@temporalio/client|worker|workflow|activity|testing 1.25.0`, `@langchain/core 1.4.0`, **`@langchain/langgraph 1.7.3`** (the syllabus pins 1.7.4; it fell inside pnpm 12's minimum-release-age window, so the previous release is pinned, as with `ai` in 0.1.0). `pnpm-workspace.yaml` allows the `@swc/core` build (Temporal's workflow bundler).
- Rust: `rmcp 3.10.0` (features `server`, `macros`, `schemars`, `transport-io`; `client` in tests), toolchain 1.100.0.
- Kotlin: `io.modelcontextprotocol:kotlin-sdk-server|client|testing 0.16.0`.

### Findings worth knowing (measured in this repo)
- The Python `mcp` client defaults to version negotiation (`mode="auto"`); the TS client defaults to `'legacy'` (2025-11-25). A hand-wired TS `server.connect(transport)` serves only the 2025 era; `serveStdio(factory)` serves both. `rmcp` 3.10.0 negotiates 2026-07-28. The Kotlin SDK 0.16.0 tops out at 2025-11-25.
- Unknown tools: the Python server returns an `is_error` result, the Rust server a JSON-RPC error. The contract accepts either.

### Known gaps / untested
- **Mastra workflows** (L7.6), the **OpenAI Agents SDK Temporal integration** (L8.2), **DBOS / Restate / Inngest** (L8.3): described, not installed or run.
- **MCP Inspector**, the **TS v1 → v2 codemod**, **OAuth / Client ID Metadata Documents**, the **tasks extension**, `createMcpHandler` (TS HTTP) and the media-probe `--http` mode: described, not exercised. (The adb server's HTTP mode and Streamable HTTP in tests were run.)
- **Android Studio Agent Mode**, **`@mobilenext/mobile-mcp`**, **`@playwright/mcp`**, **AppFunctions**, real **devices/emulators** (the adb server and the GUI graph use fakes/simulators). The Android SDK is **not installed** (awaiting approval).
- Kotlin MCP server: JVM target only, not part of the cross-language contract; 2026-07-28 not supported by the SDK version.
- A real **2-hour recording** (M8) and real ffmpeg scene detection / ASR / OCR models (M7) were not run; tests use generated clips, fixtures and fake models. ffmpeg in CI/local is the distro package (7.1.x locally), not the syllabus's pinned 9.0.2 container build.

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
