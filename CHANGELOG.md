# Changelog

All notable changes to the course. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.8.0] - 2026-11-24 (weekly freshness update of 23 Nov 2026)

Applies the updates from the 23 Nov 2026 weekly check, approved by Arunkumar ("Apply all of the updates"). Pins re-checked against their registries and GitHub releases on 24 Nov 2026. Releases less than 24 hours old on 24 Nov were not pinned (see "Skipped").

### Security / supply chain (HIGH)
- **M12 governance, "Supply chain: when the agent adds a dependency"**: the `agent-framework` 1.26.1 / 1.26.2 incident (17 Nov 2026, published 33 minutes apart, both quarantined and removed from PyPI; 1.26.0 is the last good release). 1.26.1 shipped `agent_framework_meta.pth` and 1.26.2 `af_runtime_diag.pth`, which run at every interpreter start; 1.26.2 also asked for GitHub Actions OIDC tokens. The lesson covers exact pins with hashes, a release-age cooldown, startup-hook scanning (`.pth` import lines, Python 3.15 `.start` files) and short-lived, job-scoped CI tokens, plus a C++/Rust note (Cargo.lock checksums, `build.rs`).
- New tested example `examples/python/m12/supply_chain.py` (`audit_requirements`, `scan_startup_hooks`, `cooldown_violations`, `workflow_token_findings`) with 8 tests in `test_supply_chain.py` and fixtures. The tests also run the checker on this repo: the real venv, both workflows, `uv.lock` hashes and pnpm's `minimumReleaseAge`.
- Quiz question **m12q7**. **M10** rules files: an aside on a dependency rule. **M11** review checklist: read the lockfile diff.
- **24-hour cooldown** for the course's own deps: `[tool.uv] exclude-newer = "1 day"` in `python/pyproject.toml` (`uv.lock` records `exclude-newer-span = "P1D"`) and `minimumReleaseAge: 1440` in both `pnpm-workspace.yaml` files. `AGENTS.md` now says new dependencies need the owner's OK, exact pins, lockfiles and the 1-day cooldown.
- **ONNX Runtime GitHub outage**: github.com/microsoft/onnxruntime and related repos (onnxruntime-genai among them) have returned 404 since about 03:50 IST 18 Nov 2026. A caution in **M13** quantization and a note in SYLLABUS §2.3: PyPI (1.32.0), Maven (1.32.0) and npm (1.31.1) packages still install, but `onnxruntime-node`'s Linux postinstall fetches from GitHub and fails, and third-party mirrors are not byte-identical. The course doesn't link the repo while it's down.

### Changed (versions)
- **rmcp** 3.10.0 → **3.11.0** (M9, P3 `media-probe`). Unadvertised capability methods now return `-32601` (method not found); `tests/contract.rs` asserts this, and the assertion fails on 3.10.0. The M9 Kotlin/Rust page has a "What changed in 3.11.0" paragraph.
- **browser-use** 1.0.6 → **1.0.8** (M15, M6). 1.0.8 adds `judge_cached` (the judge runs as one more turn of the cached run, falling back to a separate `judge_run`). New `judge_cost()` in `browser_use_notes.py` (13 tests) and a pins test for `judge_cached` / `CACHED_DROPPED` (6 tests). It still pins `pydantic-ai-slim==2.66.0` / `pydantic==2.14.3`, so CI keeps checking it in an isolated env. The L15.2 heading changed to "browser-use 1.0.4 → 1.0.8: four small lessons in ten days", and the M6 and M15 links follow it.
- **Spec Kit** v1.4.0 → **v1.4.3** (M10, CI `speckit` job, quiz m10).
- **FFmpeg** 9.0 → **9.1 "Gauss"** (20 Nov) in M14, the syllabus and the versions page. 9.1 adds a `libcurl` protocol (`libcurl:https://…`, `-prefer_libcurl 1`; default whitelist `http,https,libcurl`). M14 has a caution, and Ex 14.2's allowlist test and the M14 Python tests now reject both forms.
- **pydantic-ai-slim** 2.68.0 → **2.71.0** (2.69.0 folds `RequestInput` into `HandleDeferredToolCalls`; 2.71.0 renames `PeerNetwork` to `PeerConnection`; the course uses neither), **pydantic** 2.14.3 → 2.14.4, **langgraph** 1.2.22 → 1.2.24, **inspect-ai** 0.3.290 → 0.3.291, **openai** 3.51.0 → 3.57.0 (`live` extra). The lockfile also moved `langgraph-prebuilt` 1.1.3, `pydantic-core` 2.50.5, `pydantic-graph` 2.71.0.
- **@temporalio/*** 1.25.0 → 1.26.0, **@langchain/langgraph** 1.7.4 → 1.7.5 (lockfile: `langgraph-sdk` 1.17.0, `langgraph-checkpoint` 1.2.3), **Astro** 7.4.12 → 7.4.13.
- **AGP** 9.5.1 → 9.5.2 (KMP, P6).
- **ONNX Runtime GenAI** 0.19.0 → 0.20.0 (M13, syllabus `ondevice`), noted as registries-only.
- Syllabus pins and notes only: OpenAI Agents SDK 0.24.0 → 0.25.0 (RunState schema 1.22, Runloop sandbox removed, concurrent MCP Streamable HTTP), claude-agent-sdk 0.2.182 / 0.3.325 → 0.2.187 / 0.3.330, Arize Phoenix 21.0.0 → 22.0.1, Logfire 5.6.0 → 6.0.0.

### Content
- **AppFunctions**: the Jetpack library is 1.0.0 stable (18 Nov 2026). M13 tool calling, M15 and P6 say so, and note that the Android overview page still says "experimental preview" and ML Kit's docs still use alpha13.
- **Jules** (M11 landscape): read-only since 11 Nov, shuts down 31 Dec 2026.
- **TM Forum IG1554** (M1 L1.4 footnote, syllabus §2.1): team-approved 29 Oct, published 16 Nov 2026, marked Alpha / pre-production. tmforum.org returns 403 to automated checkers, so it's in `.lycheeignore`.
- M3 frameworks: the Pydantic AI renames. M5, M6, M7, M8 and P2/P4/P6/P7/P8 pages and specs updated to the new pins.

### CI
- `deploy.yml`: top-level permissions are now `contents: read`. `pages: write` and `id-token: write` move to the `deploy` job, so the build job (which runs `withastro/action` and installs packages) can't mint OIDC tokens. The new M12 checker found this.
- `python` job: browser-use pins step uses 1.0.8. `speckit` job uses v1.4.3.

### Skipped (with reason)
- **Compose BOM 2026.11.01**: tried and reverted to 2026.09.00. Its Compose 1.13.0 libraries need compileSdk 37.1 (`:p6-app:checkDebugAarMetadata` failed on 37.0). Moving to compileSdk 37.1 is for a later update.
- **LiteRT 2.4.0**: a syllabus note only; the pin is unchanged until it's tested on device.
- **AppFunctions Gradle dependency**: none added; the course has no AppFunctions build yet.
- Releases less than 24 hours old on 24 Nov (the new cooldown): inspect-ai 0.3.292, claude-agent-sdk 0.2.188 / 0.3.331, openai 3.58.0, logfire 6.0.1, Spec Kit v1.4.4, openai-agents 0.26.0.

### Not run / untested
- The `deploy.yml` permissions change only runs on a push to main, so it's untested until the next merge.
- No device, emulator or Galaxy A73 run. No real LLM, browser-use agent or judge call. FFmpeg 9.1's binary isn't run (the libcurl tests check the allowlist logic, not ffmpeg). LiteRT-LM and genai-agent with AppFunctions 1.0.0 aren't built.

## [0.7.0] - 2026-11-17 (weekly freshness update of 16 Nov 2026)

Applies all six updates from the 16 Nov 2026 weekly check, approved by Arunkumar. Pins re-checked against their registries and GitHub releases on 17 Nov 2026.

### Changed (versions)
- **browser-use** 1.0.3 → **1.0.6** (M15, syllabus `cua` group). It isn't in `uv.lock`: browser-use pins `pydantic-ai-slim==2.66.0` and the course pins 2.68.0, so CI checks it in an isolated env.
- **temporalio** (Python) 1.36.0 → **1.36.1** (M8, P4).
- **Astro** 7.4.11 → **7.4.12**, **Starlight** 0.42.11 → **0.43.1** (site).
- Patch bumps: **langgraph** 1.2.22, **@langchain/langgraph** 1.7.4 (package.json said 1.7.3 while the syllabus said 1.7.4; now both say 1.7.4), **@langchain/core** 1.4.1, **inspect-ai** 0.3.290, **playwright** (Python) 1.65.2 (Chromium 159), **ai** 7.0.173, **openai** 3.51.0 (`live` extra). The lockfile also moved these transitive packages: `@langchain/langgraph-sdk` 1.16.0, `@ai-sdk/gateway` 4.0.146, `@ai-sdk/provider-utils` 5.0.81, `@ai-sdk/provider` 4.0.38. **claude-agent-sdk** 0.2.182 (Python) / 0.3.325 (TS) in the syllabus pins (neither is installed by the course yet).
- **llama.cpp** build b12359 (the v1.0.0 build) → **b12428** (16 Nov 2026; v1.0.0 is still the latest tag) in CI, M13 and the versions page.

### Content
- **M15 L15.2** browser-use 1.0.4 → 1.0.6 as three lessons. **1.0.6**: with no `llm`, it now runs `bu-4.0` ($1.80 / $9.00 per 1M input / output tokens against `bu-fast`'s $0.12 / $0.60), so always pass `llm=`. **1.0.5**: the run judge (`result.judgement`: `success`, `failure_reason`, `description`, `prompt_injection_detected`, `bot_block_or_captcha_detected`, `gotchas`; `judge_context=`, `judge=False`) turned into an eval row where a state checker wins. **1.0.4**: screenshots are dropped in a batch so the prompt cache keeps working (BU Bench v2.1: same score, $0.434 → $0.208 per task). New tested example `examples/python/m15/browser_use_notes.py` with 12 tests. `test_browser_use_pins.py` (5 tests) checks its constants against the real 1.0.6 package. M6 L6.6 and M15 L15.6 link to it.
- **M8 L8.5** "SDK upgrades change behaviour too: logic flags": temporalio 1.36.1 turns single-batch activation (flag 2) off again by default for unflagged workflows. Two new tests: a new history records no flag 2, and a v1 history recorded on 1.36.0 (`examples/python/m8/fixtures/publish_v1_temporalio_1.36.0.json`, flag 2 set) still replays.
- **M9 L9.1** "How the spec evolves": the six-month MCP spec release cycle (SEP-3398, announced 11 Nov 2026). Releases land on the last Tuesday of March and September, and the next is targeted for 30 March 2027. The section covers the soft freeze, Tier 1 SDK betas and hard freeze, and what they mean for your servers and clients.
- **M1 L1.4**: Flatiron Health's four-layer **Agentic Maturity Model** (9 Nov 2026; Manual, Interactive, Structured, Autonomous, each with the human's and the agent's role), described as the source does. A new three-way comparison table (DORA, Thoughtworks Radar, Flatiron), a new "Try it" step, and quiz question m1q9.
- **M13 L13.6** table re-measured on b12428. Quality numbers were unchanged within noise (Q4_0 PPL 5.939 vs 5.944 on b12359 in back-to-back runs). The `-ctk q8_0` failure was reproduced on both builds. Ex 13.2 keeps the 14 Nov b12359 table as fixed input.
- M7 page: the 1.7.3 pin note was replaced, now that 1.7.4 is past pnpm's minimum-release-age window.

### Site
- Starlight 0.43 uses Astro's default `attribute` scoped-style strategy instead of forcing `:where()`. We compared Playwright screenshots of the built site before and after the bump: home, M7 overview with a quiz answered, M1 L1.4, M1 exercises with solutions open, M15 L15.2 and P8, in light and dark at 1280×900, plus a mobile 390×844 page and open menu. **0 changed pixels** on all 14. The theme select (refactored in 0.43) switched dark / light / auto and persisted across a reload, the same as before. No CSS changes were needed.

### Fixed
- Versions page (generated by `site/scripts/generate.mjs`) and README: they no longer say the KMP Android target isn't built. The Android SDK is installed, and CI's `android` job builds and tests the KMP Android target and P6's APKs (instrumentation APK compiled only). Device, emulator and Galaxy A73 runs are still untested.

### CI
- `python` job: new step running `test_browser_use_pins.py` with `uv run --isolated --no-project --with browser-use==1.0.6` (`M15_REQUIRE_BROWSER_USE=1` turns a skip into a failure). `verify.sh python` runs it too.
- `llamacpp` job downloads `llama-b12428-bin-ubuntu-x64.tar.gz`.

### Not run / untested
- No browser-use agent, gateway model or judge call (they need a Browser Use key). The judgement examples are hand-written in the real `Judgement` shape and validated against it. The cache-cost model is a toy and doesn't reproduce BU Bench.
- claude-agent-sdk and openai are pins only. The course has no installed or tested example for either (openai is in the `live` extra, which CI doesn't install).
- The A73 and emulator gaps from 0.6.0 are unchanged.

## [0.6.0] - 2026-11-14 (projects P1–P8)

### Content
- **P1 Mini-SWE** (`projects/p1`): a coding agent that goes issue → plan → edit → test → PR against a local git sandbox (bare `origin`, PRs recorded by a JSON "forge"; **no GitHub repo is created or touched**). Guarded tools (path allowlist, symlink check, hidden `.git`, read-only tests, node-id-only `run_tests` with a scrubbed env, disabled host plugins and a no-network `sitecustomize`, truncation), a budgeted loop that verifies `finish` itself, PR bodies with a measured before/after test report, and a **15-seeded-bug benchmark**. The model is scripted (mutation-search repair), not an LLM. Starter, reference solution and 24 evals; CI requires the solution to pass and the starter to fail.
- **P2 Graph research agent** (`projects/p2`, LangGraph 1.2.21): supervisor → parallel researcher workers (`Send`, `RetryPolicy` on transient search errors, other-year sources dropped, duplicates merged at fan-in) → writer → critic (numbers, content words and the cited document must agree) with capped reflection → human `interrupt` (approve / reject / edit) that survives a restart via the checkpointer; OpenTelemetry spans per node; an eval suite for trajectory, gold recall, strict citation precision, cost and simulated critical-path latency. Fictional corpus (an invented city), mock LLM that can be told to be sloppy. 17 evals.
- **P3 Media MCP toolkit** (`projects/p3`): a Python `media-toolkit` server (mcp 2.3.0) with 11 tools over real ffmpeg/GStreamer (`probe`, `loudness`, `detect_scenes`, `detect_silence`, `extract_frames`, `transcode` with a preset allowlist + confirmation + progress, `cut`/`concat` from an EDL with overwrite confirmation, `validate_pipeline`, `run_pipeline`, `live_detect` that refuses without `onnxinference`), paths locked to a media root, and Streamable HTTP as an OAuth resource server (401 + metadata, audience check, `media:write` per tool). A TypeScript subset server (@modelcontextprotocol/server 2.4.0); one contract run against Python (in-process and stdio), TypeScript and the **Rust `rmcp` 3.10.0** probe/loudness server on both protocol revisions; an agent client whose router sends `probe`/`loudness` to Rust; objective output evals (duration, streams, independent `ebur128` loudness, cut positions). A **Kotlin** adb port (`screenrecord`, `pull`, `transform` by intent) on the MCP Kotlin SDK 0.16.0, tested on the JVM with fakes. 26 Python evals, 3 TS evals, 3 Kotlin tests; CI's rust job runs the P3 evals with `P3_REQUIRE_ALL=1`.
- **P4 Durable triage workflow** (`projects/p4`, temporalio 1.36.0): classify → gather logs (retried) → propose a config change → human decision as a signal (reminder after 1 day, expiry after 3, approve / edit / reject) → apply → verify → roll back if unhealthy; escalation when no safe change exists. Side effects are exactly-once under idempotency keys; a worker killed with `SIGKILL` after applying is replaced without re-applying; v1 replays the deployed v0's histories thanks to `workflow.patched`. Runs on Temporal's local time-skipping and dev servers. 8 fictional incidents, 14 evals.
- **P5 Capstone** (`projects/p5`): a fictional legacy team repo (Python + TypeScript + Rust, roughly L1, with real traps: a README pointing at a missing Makefile, a two-second "staging" test, no TS tests, Rust tests behind `--features full`); artefact detection plus the team's M1 worksheet fed into M12's ladder; an overlay that makes the repo agent-friendly (AGENTS.md `Verify:`, `verify.sh`, fast tests in three languages, CI, PR template, CODEOWNERS, review policy, a Spec Kit spec, a skill); a before/after bench with M10's mock agent on 10 seeded tasks and hidden acceptance tests; deliverables (generated assessment and dashboard, adoption plan checked by `plan90`, retrospective). 7 evals.
- **P7 Multimodal media-analysis graph** (`projects/p7`, LangGraph 1.2.21): probe → segment (ffmpeg scene cuts fused with silence edges) → `Send` fan-out per segment (real keyframe colour and audio level, mock ASR with a `RetryPolicy`, `max_concurrency`) → supervisor merge (chapters, titles, summary, search index) → optional highlight reel through the P3 server's `cut` tool over MCP → verify (monotonic chapters, reel duration, cut position, loudness) → human `interrupt` before publishing. Local vs cloud profiles with mock models and placeholder cost/latency. 10 generated recordings, 9 evals.
- **P8 Mobile/computer-use agent graph** (`projects/p8`, LangGraph 1.2.21, Playwright 1.65.1): observe → plan → guard (policy engine; `interrupt` for a human on requested consequential actions; blocks unrequested ones and any consequential action while an injection is on screen) → act → verify (frame diff) → recover, checkpointed so a run resumes after the environment drops; step/time/cost budgets in the graph. Anthropic `computer_toolset_20260801`, OpenAI Responses `computer` and vendor-neutral JSON adapters into one action type. 20 tasks (10 web in real Chromium on M15's sandbox app, 10 mobile on M15's FakeAndroid over adb argv), 180 recorded trajectories (3 seeds × 3 adapters) that CI replays and must reproduce exactly. 12 evals.
- **P6 Field Notes** (`projects/p6`, Kotlin 2.4.21, Koog 1.3.0, AGP 9.5.1): a Koog graph-strategy agent in KMP `commonMain` with six tools (search, create, tag, summarise, delete, share), human approval on `delete_*`/`share_*` through a persisted `PendingAction`, a privacy router (cloud only when allowed, online, long, and free of private notes, emails and phone numbers), and sessions saved after every step so history and a pending approval survive process death. `androidMain` uses Koog's LiteRT-LM client (1.3.0-beta, preview) with FunctionGemma 270M on the CPU; a Compose app (no `INTERNET` permission) with an approval dialog. 20 golden prompts; a deterministic `FakeLocalModel` router (and a weaker keyword baseline) runs them in CI. 9 evals run on the JVM and as Android host tests; instrumentation tests (UI, golden on LiteRT, airplane-mode check) are compiled only. Starter/solution via `-Pp6.variant`.
- **Android SDK and KMP Android target**, approved by the owner on 14 Nov 2026: `kmp/shared` now also builds as an Android library (`com.android.kotlin.multiplatform.library`, compileSdk 37, minSdk 29) and runs its 26 commonTests as Android host tests. New CI `android` job: installs `platforms;android-37.0` and `build-tools;36.0.0` with `sdkmanager`, accepts the licences, then runs host tests, `:p6-app:assembleDebug`, the app's unit test and `assembleDebugAndroidTest`. The `kmp` job also runs P6's JVM evals and checks that the P6 starter fails.
- New `projects/` layout (`spec/`, `common/`, `starter/`, `solution/`, `evals/`), a *Projects* site section, and `check_exercises.py` now covers projects (`PROJECT_VARIANT`).

### Measured (course box)
- P1 benchmark: 13/13 fixable bugs resolved, 2/2 needing new logic escalated, 0 test files touched; 12 of 13 fixes restore the original line (`mean` was fixed by an equivalent edit); mean 4.1 test runs and ~2,200 estimated tokens per bug.
- P2 suite (5 questions, sloppy first draft, one transient search failure per query): trajectory, gold recall and citation precision all 1.0; one revision per answered question; the simulated critical path is 38.3 s vs 45.1 s sequential.
- P3 agent edit of the fixture match (scripted editor): routes probe/loudness to Rust; EDL 4.00–5.56 s + 8.48–10.08 s; output 3.2 s with video and audio, −15.9 LUFS by `ebur128` (target −16), scene cut at 1.6 s.

- P4 suite (8 incidents, flaky log tool): classification and cause 8/8; 4 resolved, 1 rolled back (an approver's edit that didn't fix it), 1 rejected, 1 expired after 72 h, 1 escalated; zero unapproved changes; kill -9 test: apply attempted by A then B, applied once.
- P5 bench (mock agent, 10 seeded tasks): success 30% → 100%, rework 70% → 0%, agent verify runs 11 → 18; review time per PR 15 → 5 min by the course's stated proxy.
- P7 comparison (10 recordings, 80 s of media per profile): boundary F1 1.0 for both; WER 0.142 local vs 0.047 cloud (mock ASR); judge pass 7/10 local (it caught the invented sponsor on 3) vs 10/10 cloud; measured graph wall time 4.2–4.3 s per media minute; cost and simulated latency are placeholders.
- P6 (JVM, fake router): golden trajectory and state 20/20; keyword baseline trajectory 12/20, state 16/20; debug APK 99.95 MB.
- P8 (180 recorded runs, scripted planner with 30% simulated mis-grounding): pass@1 0.767 / pass@3 1.0 for both pixel adapters (identical: same planner, same seeds), 0.95 / 1.0 for set-of-marks; 0 unrequested side effects; 6 human interventions per adapter; all failures are grounding (out of steps).

### Fixed
- CI `kmp` job: the test report now runs before the P6 starter check, so it shows the solution's results (it printed "35 tests, 5 failed" from the starter).
- Module pages (M9, M10, M11, M13, M14, M15) no longer give "no Android SDK" as the reason Android steps weren't run: the SDK is installed, but nothing has run on a device or emulator yet.

### Known gaps / untested
- P1: no LLM backend (the Pydantic AI, Claude Agent SDK and AI SDK variants are not built); no GitHub Actions background run (it would need a sandbox repo the owner creates); no container/network-namespace isolation for test runs.
- P2: no real LLM or LLM judge, no OTLP export, no LangGraph.js port; parallel wall time not measured (latency is simulated).
- P3: no real LLM; tasks extension not used (progress notifications instead); OAuth authorization server mocked; `live_detect`'s real onnx path untested (no plugin on the box or CI); TypeScript server is a subset; Kotlin uses fakes (no Media3, adb or device) and its starter isn't run in CI; no Android Studio Agent Mode. Deviation: the tool is `loudness`, not `measure_loudness`.
- P4: no real model, no TypeScript worker, no OTel export; only Temporal's local test/dev servers (no production cluster).
- P7: no real ASR, VLM, OCR or LLM (llama.cpp `mtmd` and whisper.cpp not run); cost/latency are placeholders; no TypeScript port; no Temporal durable variant; synthetic short recordings only.
- P8: no emulator, AndroidWorld or device runs (FakeAndroid only); no live model runs for any adapter; web app not in Docker; Rust frame-diff helper, ablation and Kotlin AccessibilityService not built.
- P6: nothing run on a device or emulator (UI tests, LiteRT golden suite, offline check, TTFT/tokens/s/energy); the LiteRT backend has never loaded a model and the GPU option is untested; not built: ML Kit speech for voice memos, the answer model, a cloud summariser, the Gemini Nano/AppFunctions flavour, llama.cpp JNI and the NPU stretch.
- P5: no live coding agent; capability scores are the team's own judgement; review time is a proxy formula; the team repo's CI workflow is checked as a file, not run.

## [0.5.0] - 2026-11-14

### Content
- Modules **M13–M15** built: 28 pages (M13 on-device & Android agents: 10; M14 multimedia & multimodal agents: 9; M15 computer-use & mobile-use agents: 9), Python, TypeScript and Kotlin/JVM examples, 9 CI-checked exercises (solution passes, starter fails; one in TypeScript) plus 2 reading exercises marked untested (Ex 13.4, Ex 14.4), and 3 quizzes (M13 9, M14 8, M15 8 questions). New site groups: *On-device & Media* (M13–M14) and *GUI Agents* (M15).
- M13 (**host side only**): a decision matrix with hard vetoes; the ML Kit GenAI availability → UI state machine in Python and KMP commonMain, with the Galaxy A73's expected answers taken from the docs; a KMP voice-notes agent (tools defined once and also exposed over the MCP Kotlin SDK, HITL-gated delete, single-thread engine owner, golden evals in commonMain; 8 new jvmTests); a PII-first hybrid router (Python and Kotlin) with Firebase AI Logic's modes mapped; a runtime comparison with versions and licences checked on GitHub; **real llama.cpp v1.0.0 (build b12359) runs on x86 CPU** — `llama-quantize` Q8_0/Q4_K_M/Q4_0 of `stories15M`, perplexity, KL divergence vs F32 and `llama-bench`; and ONNX Runtime 1.32.0 dynamic int8 quantization of a small MLP.
- M14: ffmpeg/ffprobe as sandboxed agent tools (path checks, probe, scene cuts, silences, EBU R128 loudness, thumbnails, frame-accurate cuts with two-pass loudnorm); a GStreamer pipeline validator (element allowlist, relative paths, required `num-buffers`) that also runs real `gst-launch-1.0` pipelines and parses `level` messages; a speech pipeline (VAD, toy diarization, scripted ASR, streaming vs batch latency, WER); a budgeted vision cascade; a media judge that fails closed; and the **highlight-reel worked example** (Python and TS): plan an EDL from transcript + scene cuts, render with real ffmpeg, verify duration, streams, loudness and cut points.
- M15: a local sandbox mail + calendar web app with a seeded prompt-injection email, driven with **Playwright 1.65.1 + Chromium** by three agents (pixels with simulated vision noise, accessibility tree + set-of-marks, direct API) with a guard (injection scan, confirmation for consequential actions, egress allowlist, audit log with screenshot hashes) and replay; a mobile agent against a fake `adb`/uiautomator device (idle detection, recovery); and a mini benchmark with pass@k.

### CI
- `python` job installs GStreamer (tools, base, good plugins) and Playwright Chromium; `M15_REQUIRE_BROWSER=1` makes a missing browser a failure.
- `typescript` job installs ffmpeg for the M14 highlight-reel test.
- New `llamacpp` job: downloads the llama.cpp b12359 Ubuntu x64 release and `stories15M.gguf`, runs the M13 quantization test with `M13_REQUIRE_LLAMA=1` and prints the table.

### Measured on the course box (x86 CPU; not a phone)
- llama.cpp b12359, stories15M, 4 threads, 128-token context: F32 98.4 MB / PPL 5.282; Q8_0 26.7 MB / PPL 5.289 / mean KLD 0.0011 / 97.4% same top-1; Q4_K_M 21.0 MB / 5.429 / 0.0269 / 90.7%; Q4_0 19.1 MB / 6.02 / 0.1242 / 82.9%. Q4_K_M generated more slowly than Q4_0 and Q8_0 on this CPU. Repeated runs moved Q4_0's perplexity between 5.94 and 6.02.
- ONNX Runtime int8: 68.2 KB → 19.0 KB, accuracy 0.996 → 0.996, 100% agreement.
- M15 three ways (3 seeds): pixels 9.7 steps / 0.7 invalid actions / 0.90 s; accessibility tree 6.0 / 0 / 0.65 s; API 4.0 / 0 / 0.01 s; all succeeded. Mini benchmark (10 instances, slip 0.15): pass@1 0.77, pass@3 1.00.

### Findings worth knowing (observed in this repo)
- The llama.cpp `v1.0.0` GitHub release carries no binaries (only `nightly-tag.txt`); the matching build is `b12359`, whose tools report `1.0.0-dev (build 12359)`.
- `-ctk q8_0` fails on stories15M: "K cache type q8_0 with block size 32 does not divide n_embd_head_k=48".
- ffmpeg's `select='gt(scene,…)'` missed a cut between red and green shots (similar luma); the fixture uses colours that differ in brightness and the lesson says why.
- Measuring loudness and encoding in two encodes stretched a 3.52 s cut to 3.60 s; measuring into the null muxer and encoding once fixed it.
- `gst-launch-1.0 -q` hides bus messages; GStreamer 1.28 prints `level` values as `(double){ … }` rather than `< … >` (the parser accepts both).

### Deviations from the syllabus
- CI uses the Ubuntu ffmpeg and GStreamer packages, not a pinned FFmpeg 9.0.2 container; media fixtures are generated with lavfi rather than CC-licensed clips in `media-fixtures/`.
- Ex 13.2 checks the decision half against the measured box table; the real llama.cpp run lives in the example and the `llamacpp` CI job. Ex 14.1 covers the host half only; Ex 14.3 uses synthetic data; Ex 15.3 uses the course sandbox instead of AndroidWorld. Koog is described, not used.

### Known gaps / untested
- **Android / Galaxy A73**: nothing ran on Android, an emulator or the A73 — LiteRT-LM, Gemini Nano / ML Kit GenAI, `AgentRunner`, AppFunctions, the ORT QNN EP, ExecuTorch, the MediaPipe → LiteRT-LM migration (Ex 13.4), `MediaExtractor` (Ex 14.4), the KMP Android target and the A73 benchmark table. The Android SDK is **not installed** (awaiting approval).
- **Real models**: no real ASR, VLM or LLM in M14/M15 (scripted/simulated); silero-vad, faster-whisper, whisper.cpp, pyannote, PySceneDetect, MediaPipe, PyAV, PyGObject and GStreamer `onnxinference` are described, not run.
- **GUI**: provider computer-use APIs, browser-use, Playwright MCP, E2B/cua, real devices or emulators, uiautomator2, mobile-mcp, and AndroidWorld/OSWorld/WebArena were not run.

## [0.4.0] - 2026-11-13

### Content
- Modules **M10–M12** built: 16 lessons (M10 spec-driven development, rules & skills, agent-friendly repos: 6; M11 coding & background agents, TDD with agents, review workflows: 6; M12 team practice by maturity level: 4), 5 worked-example pages, Python and TypeScript examples (mock agents, real git and cargo), 8 exercises with CI-checked solutions (solution passes, starter fails; one in TypeScript) and 3 quizzes (22 questions).
- M10: **GitHub Spec Kit v1.4.0** run for real (`specify init --integration claude`); a spec parser/linter, acceptance scenarios (Spec Kit Given/When/Then and Kiro-style EARS) turned into one executable oracle, task waves; nested AGENTS.md, Cursor `.mdc` rule modes and Claude path rules modelled in Python and TS; an Agent Skills validator and progressive-disclosure catalog; a repo audit; a pre-commit secret scan and a command allowlist (Python + TS). Worked example: a Rust crate whose plain `cargo test` runs none of its feature-gated tests, measured before/after with a **scripted** agent and real cargo builds (40% → 100% of tasks really solved, 5 → 8 verify runs).
- M11: a TDD gate (approved red tests, hashes, collection counts, skips, untracked conftest), parallel agents in real `git worktree`s with conflict-aware batch planning, an agent-PR review policy (Python + TS), an issue → agent → PR pipeline with label gate, budgets, kill switch and independent test re-run, a GitHub Actions template (two jobs: key holder read-only, writer never sees the key) with a linter, and DORA's five metrics plus review latency before/after on a fictional team.
- M12: Shapiro's L0–L5 with DORA's seven AI capabilities as entry criteria and a review-load check — **labelled as this course's own synthesis** — plus policy-as-code governance with a hash-chained audit log, a 90-day plan template and checker, and a fictional six-person team's L1→L3 quarter replayed through the gates.
- The repo now practises M10: root `AGENTS.md` (setup/verify lines) plus nested `kmp/`, `rust/`, `site/` files, three `.cursor/rules/*.mdc` rules (always / auto-attached / agent-requested), two `.claude/skills/`, and `verify.sh` as the one verify command (`make` isn't assumed). Tests check all of them.
- Site: M10–M12 sidebar groups; `Exercise`/`Solution` infer the code language from the file extension (Markdown, YAML, Python, TS answers).

### CI
- New `speckit` job: installs Spec Kit v1.4.0 from its git tag with `uvx`, runs `specify init`, and checks the course parser against the real templates (skips become failures).
- `rust` job also runs the M10 agent-friendly benchmark with real cargo builds (`M10_REQUIRE_CARGO=1`).
- Exercise loader registers modules in `sys.modules` (needed for dataclasses in exercise code) with names unique per module.

### Findings worth knowing (observed in this repo)
- Spec Kit v1.4.0's generated skills use frontmatter fields outside the Agent Skills spec (`argument-hint`, `user-invocable`, `disable-model-invocation`); a strict validator flags them as warnings.
- In a fresh repo with no commits, Spec Kit's `create-new-feature.sh` created the spec directory but did not switch branches.
- `android skills add` (named in the syllabus) **is documented** in the Android CLI command reference (with `--agent`, `--all`, `--project`); it was not run. The Android CLI plugin for Claude Code/Codex is a separate route that adds the `android-cli` skill.
- `specify check` (v1.4.0) lists 40+ agent integrations, including Kiro CLI.

### Known gaps / untested
- **Kiro** was not run; its files here are hand-written in the shape its docs describe.
- **No live coding agent** (Claude Code, Codex, Copilot CLI/coding agent, Gemini CLI, Cursor cloud agents, Codex cloud) was run; the agent-friendly benchmark and issue-to-PR pipeline use scripted agents, and the workflow template's live path is untested. Real agent success rates were not measured.
- **Android**: Android Studio Agent Mode, the Android CLI and its plugin, `android skills add`, emulators, `android layout`, Journeys, Gradle Android tasks and screenshot tests — documented, not run. The Android SDK is **not installed** (awaiting approval).
- M12's team, numbers and plan are fictional.

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
