# P7 · Multimodal media-analysis graph

**After:** M7, M14 · **Language:** Python (LangGraph 1.2.21) · **Needs:** ffmpeg

Ingest a recording, split it into chapters, analyse each segment in parallel, merge the results
into chapters, a summary, a search index and an optional highlight reel, check the output
objectively, and wait for a human before publishing. Run it under a **local** and a **cloud**
profile and compare them.

```
probe ─▶ segment (scene cuts + silence edges) ─▶ Send × N: analyse ─▶ merge (supervisor)
            keyframe colour · audio level · ASR (retried)        chapters · titles · summary · index
   ─▶ [highlight reel: P3 MCP server `cut`] ─▶ verify ─▶ approve (interrupt) ─▶ publish
```

## What is real and what is mocked

| Piece | Here | In production |
|---|---|---|
| Recordings | 10 generated talks (`common/recordings.json`): coloured "slides" with a tone each, some separated by silent black pauses | real talks/meetings |
| Probe, scene cuts, silences, loudness, the reel | **real ffmpeg** (M14 `media_tools`, P3 server) | same |
| Keyframe "caption" | **real**: one frame scaled to 1×1 px, named by the nearest palette colour | a VLM caption + OCR, cheap filters first |
| ASR | **mock**: reference words with every Nth word replaced (local N=7, cloud N=19) | whisper.cpp / faster-whisper / a hosted ASR |
| Summary | **mock** template; the local profile adds "Sponsored by Acme." on 3 recordings | llama.cpp `mtmd` model / hosted model |
| Judge | M14 rubric judge with its mock judge | an LLM judge |
| Cost and latency per profile | **placeholders** in `p7_kit.PROFILES`, not prices or benchmarks | measured |

## Milestones

1. **Probe and segment.** Probe the duration; cut at scene changes.
2. **Fan out.** One `Send` per segment to `analyse`: keyframe colour, audio level, ASR. A pause
   (black + silent) gets no ASR. Bound parallelism with `max_concurrency`. Fuse the audio track:
   the cut from a black pause into a dark slide can slip under the scene threshold, but its silence edges
   don't. A transient ASR error must be retried (`RetryPolicy`), not crash the run.
3. **Supervisor merge.** Drop pauses, build chapters with (mock-LLM) titles, a summary and a
   word → chapter-start index.
4. **Highlight reel and verify.** Cut the two longest chapters' middles through the P3 server's
   `cut` tool over MCP. Verify: chapters monotonic, reel duration ±0.1 s, a cut within one frame
   of the shot boundary, loudness within 1 LU of −16 LUFS.
5. **Approve and evaluate.** `interrupt` before publishing (chapters file). Score every recording
   under both profiles: chapter-boundary F1 (±0.1 s), WER, judge pass rate, cost per media hour,
   latency; produce the comparison table.

## Evals

`PROJECT_VARIANT=solution uv run pytest ../projects/p7/evals` (9 tests; the starter fails 3:
boundaries, retry, reel).

## Not built

TypeScript port; Temporal durable variant for multi-hour files; real ASR/VLM/LLM models;
OCR; real cost and latency measurements of either profile.
