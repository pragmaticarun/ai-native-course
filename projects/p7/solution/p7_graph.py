"""P7 milestones 1-4: the media-analysis graph.

    probe -> segment (scene cuts) -> Send x N: analyse (keyframe colour, audio level, ASR;
    retried) -> merge (supervisor: drop pauses, chapters, titles, summary, search index)
    -> [highlight reel via the P3 MCP server] -> verify -> approve (interrupt) -> publish

`max_concurrency` in the run config bounds parallel workers; a worker that fails after its
retries becomes a recorded error, not a crashed run.
"""

from __future__ import annotations

import asyncio
import operator
import re
import sys
from pathlib import Path
from typing import Annotated, Any, TypedDict

import media_tools as mt
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, Send, interrupt
from p7_kit import (
    FPS,
    PROFILES,
    MockASR,
    TransientASRError,
    keyframe_color,
    mock_summarise,
    mock_title,
    p3_server_dir,
    segment_level_db,
)

SILENT_DB = -60.0
MIN_SEGMENT_S = 0.3
EDGE_S = 0.1  # slack at segment edges when matching silences
REEL_SHOT_S = 1.2
TARGET_LUFS = -16.0


class State(TypedDict, total=False):
    rec_id: str
    path: str
    profile: str
    want_reel: bool
    duration: float
    segments: list[dict[str, float]]
    results: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]
    chapters: list[dict[str, Any]]
    summary: str
    index: dict[str, list[float]]
    reel: dict[str, Any] | None
    problems: list[str]
    decision: str
    published: str


def build(asr: MockASR, checkpointer: Any = None) -> Any:
    def probe(s: State) -> State:
        return {"duration": mt.probe(Path(s["path"])).duration}

    def segment(s: State) -> State:
        path = Path(s["path"])
        # Fuse the two modalities: a dark slide after a dark slide can slip under the scene
        # threshold, but the pause's silence edges still mark it. Snap to frames, dedupe.
        # Scene cuts are frame-exact; a silence edge only counts where no cut is near (the
        # audio edge can sit a few hundredths off, and ffmpeg versions differ here).
        cuts = mt.scene_cuts(path)
        quiet = [t for a, b in mt.silences(path) for t in (a, b)]
        marks = cuts + [t for t in quiet if all(abs(t - c) > MIN_SEGMENT_S for c in cuts)]
        edges = [0.0]
        for t in sorted(round(round(m * FPS) / FPS, 3) for m in marks):
            if t - edges[-1] > MIN_SEGMENT_S and s["duration"] - t > MIN_SEGMENT_S:
                edges.append(t)
        edges.append(s["duration"])
        segs = [
            {"start": round(a, 3), "end": round(b, 3)}
            for a, b in zip(edges, edges[1:], strict=False)
            if b - a > 1 / FPS
        ]
        return {"segments": segs}

    def fan_out(s: State) -> list[Send]:
        return [
            Send("analyse", {"rec_id": s["rec_id"], "path": s["path"], **seg})
            for seg in s["segments"]
        ]

    def analyse(job: dict[str, Any]) -> State:
        path, a, b = Path(job["path"]), job["start"], job["end"]
        color = keyframe_color(path, (a + b) / 2)
        level = segment_level_db(path, a, b)
        # A pause is silent by level, or because silencedetect covers it (encoders differ in how
        # much of the neighbouring tone bleeds into the edges of a short pause).
        covered = any(x <= a + EDGE_S and y >= b - EDGE_S for x, y in mt.silences(path))
        event = "silence" if level < SILENT_DB or covered else "sound"
        pause = color == "black" and event == "silence"
        text = "" if pause else asr.transcribe(job["rec_id"], a, b)
        return {
            "results": [
                {
                    "start": a,
                    "end": b,
                    "color": color,
                    "level_db": level,
                    "event": event,
                    "pause": pause,
                    "transcript": text,
                }
            ]
        }

    def merge(s: State) -> State:
        segs = sorted(s.get("results", []), key=lambda r: r["start"])
        chapters = [
            {
                "start": r["start"],
                "end": r["end"],
                "title": mock_title(r["transcript"]),
                "transcript": r["transcript"],
                "color": r["color"],
            }
            for r in segs
            if not r["pause"]
        ]
        index: dict[str, list[float]] = {}
        for c in chapters:
            for w in set(re.findall(r"[a-z]{4,}", c["transcript"].lower())):
                index.setdefault(w, []).append(c["start"])
        summary = mock_summarise(PROFILES[s["profile"]], s["rec_id"], chapters)
        return {"chapters": chapters, "index": index, "summary": summary}

    def highlight(s: State) -> State:
        longest = sorted(s["chapters"], key=lambda c: c["start"] - c["end"])[:2]
        edl = []
        for c in sorted(longest, key=lambda c: c["start"]):
            mid = (c["start"] + c["end"]) / 2
            a = round(round((mid - REEL_SHOT_S / 2) * FPS) / FPS, 3)
            edl.append({"start": a, "end": round(a + REEL_SHOT_S, 3)})
        root, name = Path(s["path"]).parent, Path(s["path"]).name
        out = f"{Path(name).stem}_reel.mp4"
        result = asyncio.run(_cut_via_mcp(root, name, edl, out))
        return {"reel": {"path": out, "edl": edl, "error": result}}

    def verify(s: State) -> State:
        problems = []
        ch = s["chapters"]
        if not ch:
            problems.append("no chapters")
        for x, y in zip(ch, ch[1:], strict=False):
            if not (x["start"] < x["end"] <= y["start"] < y["end"]):
                problems.append(f"chapters not monotonic at {y['start']}")
        reel = s.get("reel")
        if reel:
            if reel["error"]:
                problems.append(f"reel failed: {reel['error']}")
            else:
                f = Path(s["path"]).parent / reel["path"]
                want = sum(e["end"] - e["start"] for e in reel["edl"])
                got = mt.probe(f).duration
                if abs(got - want) > 0.1:
                    problems.append(f"reel is {got:.2f}s, expected {want:.2f}s")
                boundary = reel["edl"][0]["end"] - reel["edl"][0]["start"]
                if not any(abs(c - boundary) <= 1 / FPS + 1e-6 for c in mt.scene_cuts(f)):
                    problems.append(f"no cut within one frame of {boundary:.2f}s")
                lufs = mt.loudness_lufs(f)
                if abs(lufs - TARGET_LUFS) > 1.0:
                    problems.append(f"reel loudness {lufs} not within 1 LU of {TARGET_LUFS}")
        return {"problems": problems}

    def approve(s: State) -> State:
        decision = interrupt(
            {
                "summary": s["summary"],
                "chapters": [c["title"] for c in s["chapters"]],
                "problems": s["problems"],
            }
        )
        return {"decision": str(decision)}

    def publish(s: State) -> State:
        lines = [
            f"{int(c['start'] // 60)}:{int(c['start'] % 60):02d} {c['title']}"
            for c in s["chapters"]
        ]
        out = Path(s["path"]).with_suffix(".chapters.txt")
        out.write_text("\n".join(lines) + "\n")
        return {"published": out.name}

    # langgraph 1.2.21 add_node overloads reject plain TypedDict node functions under mypy
    # (reproduced with a 10-line file), so the builder is typed Any.
    g: Any = StateGraph(State)
    g.add_node("probe", probe)
    g.add_node("segment", segment)
    g.add_node(
        "analyse",
        analyse,
        retry_policy=RetryPolicy(
            retry_on=TransientASRError, max_attempts=3, initial_interval=0.01, jitter=False
        ),
    )
    g.add_node("merge", merge)
    g.add_node("highlight", highlight)
    g.add_node("verify", verify)
    g.add_node("approve", approve)
    g.add_node("publish", publish)
    g.add_edge(START, "probe")
    g.add_edge("probe", "segment")
    g.add_conditional_edges("segment", fan_out, ["analyse"])
    g.add_edge("analyse", "merge")
    g.add_conditional_edges(
        "merge", lambda s: "highlight" if s.get("want_reel") else "verify", ["highlight", "verify"]
    )
    g.add_edge("highlight", "verify")
    g.add_edge("verify", "approve")
    g.add_conditional_edges(
        "approve", lambda s: "publish" if s["decision"] == "approve" else END, ["publish", END]
    )
    g.add_edge("publish", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())


async def _cut_via_mcp(root: Path, name: str, edl: list[dict[str, float]], out: str) -> str | None:
    """Call the P3 toolkit's `cut` tool over MCP (in-process). Returns an error text or None."""
    if str(p3_server_dir()) not in sys.path:
        sys.path.append(str(p3_server_dir()))
    from mcp import Client
    from p3_server import build_server

    async with Client(build_server(root)) as c:
        r = await c.call_tool(
            "cut", {"path": name, "edl": edl, "out": out, "target_lufs": TARGET_LUFS}
        )
        return "\n".join(getattr(x, "text", "") for x in r.content) if r.is_error else None


def run(
    graph: Any, state: State, thread: str, decision: str = "approve", max_concurrency: int = 4
) -> State:
    cfg = {"configurable": {"thread_id": thread}, "max_concurrency": max_concurrency}
    graph.invoke(state, cfg)
    out: State = graph.invoke(Command(resume=decision), cfg)
    return out
