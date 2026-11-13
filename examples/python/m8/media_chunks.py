"""M8 worked example: a long media job as a Temporal workflow.

A 2-hour recording is cut into 10-minute chunks. Each chunk is one activity that:
* writes to an idempotent output path (`<job>/chunk_0003.mp4`): if the file exists, the
  chunk is already done and the activity returns at once; output is written to `.part`
  and renamed, so a crash never leaves a half-written "done" file;
* works in 60-second pieces and heartbeats its progress; when a worker dies mid-chunk,
  the retry reads the last heartbeat (`activity.info().heartbeat_details`) and resumes
  from there instead of from the start of the chunk.

`FakeTranscoder` (used by the tests) records what would run. `FfmpegTranscoder` builds
real `ffmpeg -ss/-t` commands; it is tested on a few seconds of generated media when
ffmpeg is installed (the Rust CI job installs it), never on a real 2-hour recording.
"""

from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Protocol

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

CHUNK_S = 600
PIECE_S = 60
TASK_QUEUE = "m8-media-chunks"


@dataclass
class Chunk:
    job: str
    source: str
    index: int
    start_s: float
    duration_s: float


def plan_chunks(job: str, source: str, total_s: float, chunk_s: float = CHUNK_S) -> list[Chunk]:
    chunks, start, i = [], 0.0, 0
    while start < total_s:
        chunks.append(Chunk(job, source, i, start, min(chunk_s, total_s - start)))
        start += chunk_s
        i += 1
    return chunks


@dataclass
class ChunkResult:
    index: int
    skipped: bool
    resumed_from: float | None


class Transcoder(Protocol):
    def piece(self, chunk: Chunk, offset_s: float, length_s: float, part: Path) -> None: ...


def ffmpeg_args(src: str, start_s: float, length_s: float, out: Path) -> list[str]:
    """`-ss` before `-i` seeks fast; `-t` bounds the piece; stream copy keeps it cheap."""
    return ["ffmpeg", "-v", "error", "-y", "-ss", f"{start_s:.3f}", "-t", f"{length_s:.3f}",
            "-i", src, "-c", "copy", "-f", "mpegts", str(out)]  # fmt: skip


class FfmpegTranscoder:
    def piece(self, chunk: Chunk, offset_s: float, length_s: float, part: Path) -> None:
        tmp = part.with_suffix(f".{int(offset_s)}.ts")
        subprocess.run(
            ffmpeg_args(chunk.source, chunk.start_s + offset_s, length_s, tmp), check=True
        )
        with part.open("ab") as f:  # mpegts pieces can be concatenated byte-wise
            f.write(tmp.read_bytes())
        tmp.unlink()


@dataclass
class FakeTranscoder:
    """Records pieces; can crash once at (chunk, offset) to simulate a dying worker."""

    crash_at: tuple[int, float] | None = None
    pieces: list[tuple[int, float]] = field(default_factory=list)

    def piece(self, chunk: Chunk, offset_s: float, length_s: float, part: Path) -> None:
        if self.crash_at == (chunk.index, offset_s):
            self.crash_at = None
            raise RuntimeError(f"worker died in chunk {chunk.index} at +{offset_s:.0f}s")
        self.pieces.append((chunk.index, offset_s))
        with part.open("a") as f:
            f.write(f"{offset_s}\n")


class ChunkActivities:
    def __init__(self, out_dir: Path, transcoder: Transcoder) -> None:
        self.out_dir, self.transcoder = out_dir, transcoder

    def output_path(self, chunk: Chunk) -> Path:
        return self.out_dir / chunk.job / f"chunk_{chunk.index:04d}.mp4"

    @activity.defn(name="process_chunk")
    async def process_chunk(self, chunk: Chunk) -> ChunkResult:
        out = self.output_path(chunk)
        if out.exists():  # idempotent: a retried or replayed chunk is a no-op
            return ChunkResult(chunk.index, skipped=True, resumed_from=None)
        out.parent.mkdir(parents=True, exist_ok=True)
        part = out.with_suffix(".part")
        details = activity.info().heartbeat_details
        offset = float(details[0]) if details else 0.0
        resumed_from = offset if details else None
        if offset == 0.0 and part.exists():
            part.unlink()  # stale partial output from an attempt that never heartbeated
        while offset < chunk.duration_s:
            length = min(PIECE_S, chunk.duration_s - offset)
            self.transcoder.piece(chunk, offset, length, part)
            offset += length
            activity.heartbeat(offset)  # progress survives the worker
            await asyncio.sleep(0)
        part.rename(out)
        return ChunkResult(chunk.index, skipped=False, resumed_from=resumed_from)


@workflow.defn
class LongMediaJob:
    @workflow.run
    async def run(self, job: str, source: str, total_s: float) -> list[ChunkResult]:
        results: list[ChunkResult] = []
        for chunk in plan_chunks(job, source, total_s):
            results.append(
                await workflow.execute_activity(
                    "process_chunk",
                    chunk,
                    result_type=ChunkResult,
                    start_to_close_timeout=timedelta(minutes=30),
                    heartbeat_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(initial_interval=timedelta(milliseconds=100)),
                )
            )
        return results
