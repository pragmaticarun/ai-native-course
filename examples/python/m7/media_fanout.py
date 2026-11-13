"""M7 worked example: media fan-out graph (the core of project P7).

split into scenes -> fan out per (scene, task) for ASR, frame captioning and OCR -> merge
into chapters. `max_concurrency` bounds how many workers run at once (on a laptop or a
phone you can't run 60 model calls in parallel), and a failed worker becomes a recorded
error instead of failing the whole graph.

The workers are deterministic fakes over a scene list. With real media, `split` would run
ffmpeg scene detection (`select='gt(scene,0.4)',showinfo`) and the workers would call
whisper.cpp, a vision model and an OCR model; that path is not run here (untested).
"""

from __future__ import annotations

import asyncio
import operator
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

SCENES = [  # (start_s, end_s, what a real model would hear / see / read)
    (0.0, 42.0, "welcome to the AV1 deep dive", "speaker at a desk", "AV1 DEEP DIVE"),
    (42.0, 180.5, "tiles let decoders run in parallel", "diagram of frame tiles", "TILES"),
    (180.5, 300.0, "film grain synthesis saves bits", "grainy film clip", ""),
    (300.0, 345.0, "thanks for watching", "end card", "SUBSCRIBE"),
]
TASKS = ("asr", "caption", "ocr")

Worker = Callable[[int, str], Awaitable[str]]


class Media(TypedDict, total=False):
    source: str
    scenes: list[dict[str, Any]]
    results: Annotated[list[dict[str, Any]], operator.add]
    chapters: list[dict[str, Any]]
    errors: list[str]


class Meter:
    """Records peak concurrency so tests can check the limit is respected."""

    def __init__(self) -> None:
        self.active = 0
        self.peak = 0
        self.calls = 0

    async def run(self, fn: Worker, i: int, task: str) -> str:
        self.active += 1
        self.calls += 1
        self.peak = max(self.peak, self.active)
        try:
            return await fn(i, task)
        finally:
            self.active -= 1


def fake_worker(fail: frozenset[tuple[int, str]] = frozenset()) -> Worker:
    async def work(i: int, task: str) -> str:
        await asyncio.sleep(0.005)
        if (i, task) in fail:
            raise RuntimeError(f"{task} model timed out on scene {i}")
        return str(SCENES[i][2 + TASKS.index(task)])

    return work


def build(worker: Worker, meter: Meter):
    def split(state: Media) -> Media:
        return {"scenes": [{"i": i, "start": s[0], "end": s[1]} for i, s in enumerate(SCENES)]}

    def fan_out(state: Media) -> list[Send]:
        return [Send("analyse", {"i": sc["i"], "task": t}) for sc in state["scenes"] for t in TASKS]

    async def analyse(job: dict[str, Any]) -> Media:
        try:
            text = await meter.run(worker, job["i"], job["task"])
            return {"results": [{**job, "text": text}]}
        except Exception as exc:  # a partial failure is data, not a crash
            return {"results": [{**job, "error": str(exc)}]}

    def merge(state: Media) -> Media:
        chapters, errors = [], []
        for sc in state["scenes"]:
            got = {r["task"]: r for r in state["results"] if r["i"] == sc["i"]}
            errors += [r["error"] for r in got.values() if "error" in r]
            text = {t: got[t].get("text", "") for t in TASKS}
            title = text["ocr"].title() or text["caption"].capitalize()
            chapters.append(
                {
                    "start": sc["start"],
                    "title": title,
                    "summary": text["asr"],
                    "complete": all("error" not in got[t] for t in TASKS),
                }
            )
        return {"chapters": chapters, "errors": errors}

    g = StateGraph(Media)
    g.add_node("split", split)
    # A Send target receives the Send payload, not the graph state; LangGraph's
    # add_node typing assumes the state type, hence the ignore.
    g.add_node("analyse", analyse)  # type: ignore[arg-type]
    g.add_node("merge", merge)
    g.add_edge(START, "split")
    g.add_conditional_edges("split", fan_out, ["analyse"])
    g.add_edge("analyse", "merge")
    g.add_edge("merge", END)
    return g.compile()


def youtube_chapters(chapters: list[dict[str, Any]]) -> str:
    def ts(sec: float) -> str:
        m, s = divmod(int(sec), 60)
        return f"{m}:{s:02d}"

    return "\n".join(f"{ts(c['start'])} {c['title']}" for c in chapters)


async def run(
    limit: int = 3, fail: frozenset[tuple[int, str]] = frozenset()
) -> tuple[dict[str, Any], Meter]:
    meter = Meter()
    out = await build(fake_worker(fail), meter).ainvoke(
        {"source": "talk.mp4"}, {"max_concurrency": limit}
    )
    return out, meter


if __name__ == "__main__":
    out, meter = asyncio.run(run(limit=3, fail=frozenset({(2, "ocr")})))
    print(youtube_chapters(out["chapters"]))
    print(
        "errors:", out["errors"], "| worker calls:", meter.calls, "| peak concurrency:", meter.peak
    )
