# AI-Native Software Development

A hands-on course for experienced systems engineers (C++, Rust, Android, multimedia):
AI maturity models, agent loops, graphs, MCP, on-device and GUI agents.

- **Site:** https://pragmaticarun.github.io/ai-native-course/
- **Syllabus (v0.3):** [SYLLABUS.md](SYLLABUS.md)
- **Status:** modules **M0–M3** built and tested; M4–M15 and projects P1–P8 are planned (see the syllabus).

## Run everything locally (offline, mock models)

```bash
# Python 3.13 + uv
cd python && uv sync && uv run pytest -q ../examples/python \
  && uv run python ../scripts/check_exercises.py --lang py \
  && uv run python ../scripts/validate_quizzes.py && cd ..
# TypeScript (Node 24 + pnpm 12)
pnpm install --frozen-lockfile && pnpm typecheck && pnpm test && python3 scripts/check_exercises.py --lang ts
# Site
cd site && pnpm install --frozen-lockfile && pnpm build
```

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
| `kmp/`, `rust/` | placeholders for later modules (M9, M13, P3, P6, P8) |

## Untested / not yet built
- Device and emulator steps (M3 mobile-use with `adb`): only parsing/command logic is tested, against a hand-written fixture.
- Android/KMP worked example in M2: designed, not implemented (no Kotlin compiled yet).
- OpenAI Agents SDK and Claude Agent SDK versions of the M3 explorer: comparison only, no tested code yet.
- Computer-use adapters (Anthropic/OpenAI): tested against recorded payload shapes from the docs, not against live APIs.
