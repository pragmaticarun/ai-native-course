# P3 — Media MCP toolkit + an agent that uses it

**After:** M9 (core), M14 (extended) · **Languages:** Python (full toolkit), TypeScript
(subset), Rust (`rmcp` probe/loudness, required), Kotlin (JVM, fakes) · real ffmpeg, mock model

Build `media-toolkit`, an MCP server that makes ffmpeg and GStreamer safe for an agent to
drive: read-only analysis tools, write tools that ask first and never overwrite silently, a
preset allowlist instead of free-form ffmpeg arguments, paths locked to a media root, OAuth
scopes over HTTP. Then an agent client that routes `probe`/`loudness` to the Rust server and
everything else to the Python toolkit, edits a highlight reel, and is graded by objective
checks (duration, streams, loudness, cut positions), not by a judge.

Fixtures (`common/p3_fixtures.py`) are generated with ffmpeg: `match.mp4` (10.52 s, five
colour shots, cuts at 2.0/3.52/6.04/8.04 s, silence 2.0–3.52 s), `a.mp4`, `b.mp4`, `tone.wav`.

## Milestones

| # | File | You build | Evals |
|---|---|---|---|
| M1 | `p3_server.py` | read-only tools: `probe`, `loudness`, `detect_scenes`, `detect_silence`; the path guard | `test_scene_and_silence_*`, `test_paths_outside_*`, `test_tools_are_annotated_*` |
| M2 | `p3_server.py` | write tools: `extract_frames`, `transcode` (presets, asks, progress), `cut` (EDL validation, asks before overwrite), `concat` | `test_transcode_*`, `test_declined_*`, `test_only_allowlisted_*`, `test_bad_edls_*`, `test_cut_asks_*` |
| M3 | `p3_server.py` | GStreamer: `validate_pipeline`, `run_pipeline`, `live_detect` (refuses without `onnxinference`) | `test_pipeline_*`, `test_run_pipeline_*`, `test_live_detect_*` |
| M4 | `p3_auth.py` | Streamable HTTP as an OAuth resource server: 401 + metadata, audience check, `media:write` scope per tool | `test_http_oauth_*` |
| M5 | `ts/mediaToolkit.ts` + `common/p3_contract.py` | the TS server; one contract over Python (in-process and stdio), TS and Rust `rmcp` servers on both protocol revisions | `test_contract_*`, `p3.test.ts` |
| M6 | `p3_client.py`, `p3_evals.py` | router + agent loop + objective output checks | `test_agent_*`, `test_objective_checks_*` |
| M7 | Kotlin `AdbMediaServer.kt` | adb tools (`screenrecord`, `pull`, `transform` by intent) on the MCP Kotlin SDK, with fakes | `kmp/.../course/p3/AdbMediaServerTest.kt` |

## Done when

`PROJECT_VARIANT=solution P3_REQUIRE_ALL=1 uv run pytest ../projects/p3/evals` passes (needs
`pnpm install`, `cargo build` in `rust/media-probe`, ffmpeg and gst-launch-1.0), the TS evals
pass, and `./gradlew :shared:jvmTest` passes in `kmp/`.

## Deviations from the syllabus

- The loudness tool is called `loudness` (not `measure_loudness`) so the M9 contract covers
  the Python, TypeScript and Rust servers unchanged.
- The TypeScript server is a subset: `probe`, `loudness`, `detect_scenes`, `detect_silence`,
  `transcode`. `extract_frames`, `cut`, `concat` and the GStreamer tools are Python-only.
- Long jobs report MCP **progress** notifications; the tasks extension isn't used.
- The Kotlin `transform` runs through a `MediaTransformer` interface; no Media3 code is built.

## Stretch (not built here)

The tasks extension for long transcodes; Media3 Transformer behind `MediaTransformer` on a
device; Android Studio Agent Mode over HTTP; a custom GStreamer element whose metadata is a
resource; the full toolkit in TypeScript.
