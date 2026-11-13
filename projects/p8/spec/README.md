# P8 · Mobile/computer-use agent graph with safety checkpoints and an eval harness

**After:** M6, M7, M15 · **Language:** Python (LangGraph 1.2.21, Playwright 1.65.1)

Build a GUI agent as an explicit, checkpointed graph, drive it through three model adapters, and
measure it on 20 tasks with state-based checkers.

```
observe ─▶ plan ─▶ guard ─(ask)─▶ interrupt: human approves / denies
             │        └─(allow)─▶ act ─▶ verify ─┬─▶ plan …
   budgets: steps, time, cost                     └─(2 failures in a row)─▶ recover ─▶ observe
```

## What is real and what is mocked

| Piece | Here |
|---|---|
| Web environment | **real** headless Chromium on M15's local sandbox mail/calendar app; egress allowlisted to the sandbox host |
| Mobile environment | M15's `FakeAndroid` answering the real adb argv from M3's `AdbDevice`. **Not an emulator** |
| Models | a scripted planner (reacts to observations; seeded 30% chance a click is mis-grounded), encoded into each vendor's wire format and **recorded**; CI replays the recordings |
| Adapters | Anthropic `computer_toolset_20260801`, OpenAI Responses `computer` tool, vendor-neutral JSON + set-of-marks. Tested on recorded payloads only, never against the live APIs |
| Cost | placeholder price per 1k estimated tokens |

## Milestones

1. **Graph.** `observe` (screen text + set-of-marks with values + frame hash) → `plan` →
   `guard` → `act` → `verify` (frame diff: did the screen change?) → `recover` after two failed
   steps (web: back to the inbox; mobile: back → home → relaunch). Checkpointed: when the
   environment drops mid-run, resume the same thread; side effects aren't repeated.
2. **Adapters.** One internal `Action`; each adapter decodes its vendor's turn into it and
   formats the results the vendor expects (Anthropic: one `tool_result` per `tool_use`,
   `toolset_name` echoed, halt text after a failure; OpenAI: `computer_call_output` with a
   `computer_screenshot`; neutral: JSON Schema validated).
3. **Guard.** Block consequential actions the task didn't ask for and any consequential action
   while untrusted instructions are on screen; `interrupt` for a human when the task did ask.
4. **Budgets.** Step, time and cost limits end the run in the graph.
5. **Harness.** 20 tasks (10 web, 10 mobile), 3 seeds × 3 adapters, recorded and replayed;
   pass@1, pass@3, steps, invalid actions, unsafe actions blocked, interventions, recoveries,
   cost, time and a failure taxonomy (grounding, planning, verification, safety).

`record()` in `solution/p8_harness.py` re-records every trajectory; the evals only replay.

## Evals

`PROJECT_VARIANT=solution uv run pytest ../projects/p8/evals` (12 tests; the starter fails 6).

## Not built

Emulator (Pixel 6 / API 33) and AndroidWorld runs; live model runs per adapter (nightly job);
the Docker sandbox for the web app (it runs in-process on 127.0.0.1); the Rust frame-diff
helper (Python hash diff only); the screenshot-vs-a11y ablation; the Kotlin AccessibilityService.
