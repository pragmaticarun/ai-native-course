# AI-Native Software Development

A hands-on course for experienced systems engineers (C++, Rust, Android, multimedia):
AI maturity models, agent loops, graphs, MCP, on-device and GUI agents.

- **Site:** https://pragmaticarun.github.io/ai-native-course/
- **Syllabus (v0.3):** [SYLLABUS.md](SYLLABUS.md)
- **Status:** modules **M0–M12** built and tested (Python, TypeScript, Kotlin/JVM, Rust); M13–M15 and projects P1–P8 are planned (see the syllabus).

## Run everything locally (offline, mock models)

One command (the same checks CI runs): `./verify.sh setup && ./verify.sh` (subcommands: `python`, `ts`, `exercises`, `rust`, `kmp`, `site`). Agents: see [AGENTS.md](AGENTS.md).

Or step by step:

```bash
# Python 3.13 + uv
cd python && uv sync && uv run pytest -q ../examples/python \
  && uv run python ../scripts/check_exercises.py --lang py \
  && uv run python ../scripts/validate_quizzes.py && cd ..
# TypeScript (Node 24 + pnpm 12)
pnpm install --frozen-lockfile && pnpm typecheck && pnpm test && python3 scripts/check_exercises.py --lang ts
# Rust (rustup reads rust/media-probe/rust-toolchain.toml)
cd rust/media-probe && cargo test && cargo build && cd ../..
# Kotlin (JDK 21)
cd kmp && ./gradlew :shared:jvmTest && cd ..
# Site
cd site && pnpm install --frozen-lockfile && pnpm build
```

Temporal tests (M8) download Temporal's test/dev server binaries on first run; M8/M9 media tests use ffmpeg when installed and skip otherwise.

Live mode: set `COURSE_LLM_PROVIDER` (`openai` | `anthropic`), `COURSE_LLM_MODEL` and that provider's key
(see `.env.example`). Live paths are **not** exercised in CI.

## Layout

| Path | What |
|---|---|
| `site/` | Astro Starlight site (lessons, quizzes, generated syllabus/changelog/versions pages) |
| `python/` | `uv` project: shared `aincourse` package (neutral model interface + `ScriptedModel` mock) |
| `examples/python`, `examples/ts` | every worked example shown on the site, with tests |
| `exercises/mX/exY/` | `README.md`, `starter/`, `solution/`, `tests/` (CI: solution passes, starter fails) |
| `quizzes/` | quiz YAML + JSON Schema |
| `scripts/` | exercise checker, quiz validator, type-check script |
| `kmp/` | Kotlin Multiplatform (`./gradlew :shared:jvmTest`, JDK 21); M2/M4/M5/M9 examples, JVM target only |
| `rust/media-probe/` | M9 `rmcp` MCP server (`probe`, `loudness`), used by P3 later |
| `AGENTS.md` (+ `kmp/`, `rust/`, `site/`), `.cursor/rules/`, `.claude/skills/`, `verify.sh` | the repo's own agent instructions, rules, skills and verify command (M10 practises them; tests check them) |

## Untested / not yet built
- Device and emulator steps (M3 mobile-use with `adb`): only parsing/command logic is tested, against a hand-written fixture.
- KMP: JVM target only; the Android target, devices and emulators are untested. ML Kit is mirrored with our own types.
- M6 on-device eval data is a synthetic fixture; GUI evals use the simulator only.
- promptfoo, DeepEval, Logfire/OTLP export: described, not exercised.
- OpenAI Agents SDK and Claude Agent SDK versions of the M3 explorer: comparison only, no tested code yet.
- Computer-use adapters (Anthropic/OpenAI): tested against recorded payload shapes from the docs, not against live APIs.
- M7: Mastra workflows (reading only); GUI graph and media fan-out use a simulated emulator and fake models.
- M8: OpenAI Agents SDK Temporal integration, DBOS/Restate/Inngest (reading only); no real 2-hour recording.
- M9: MCP Inspector, TS codemod, OAuth/CIMD, tasks extension, Android Studio Agent Mode, `@mobilenext/mobile-mcp`, `@playwright/mcp`, AppFunctions, real devices (not exercised). The Android SDK is not installed.
- M10: Kiro (comparison from its docs; fixture files hand-written), live coding agents on the agent-friendly benchmark (the measured agent is a script), Android CLI / `android skills add` / the Android CLI plugin, Gradle Android tasks and screenshot tests (no Android SDK).
- M11: no live coding agent, cloud agent (Copilot coding agent, Codex cloud, Cursor cloud agents) or GitHub API call; the issue-to-PR workflow template's live path is untested; Android Studio Agent Mode, Android CLI, emulator and Journeys are untested.
- M12: the team journey and its numbers are fictional; the entry criteria are the course's own synthesis.
