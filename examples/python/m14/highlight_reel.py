"""M14 worked example: the "highlight reel" agent (Python version).

probe -> scene detect -> transcribe -> score segments -> plan an EDL -> ffmpeg concat with
loudness normalisation -> verify against the plan with ffprobe.

ffmpeg/ffprobe calls are real (media_tools). The "models" are mocks: `FixedTranscriber`
returns the fixture transcript and `KeywordScorer` stands in for a multimodal model that
reads a shot's transcript and frame caption. Swap them for real ones behind the same
Protocols; the plan/verify contract does not change.

Run: cd examples/python && uv run --project ../../python python -m m14.highlight_reel
"""

from __future__ import annotations

import json
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_tools import (  # noqa: E402
    Cut,
    Shot,
    loudness_lufs,
    make_clip,
    probe,
    render,
    scene_cuts,
)

FIXTURE = Path(__file__).parent / "fixtures" / "highlight.json"
FPS = 25


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


class Transcriber(Protocol):
    def transcribe(self, path: Path) -> list[Segment]: ...


class Scorer(Protocol):
    def score(self, shot: Cut, transcript: str, caption: str) -> float: ...


@dataclass
class FixedTranscriber:
    segments: list[Segment]

    def transcribe(self, path: Path) -> list[Segment]:
        return list(self.segments)


@dataclass
class KeywordScorer:
    """Mock multimodal scorer: excitement words in speech + caption, 0..1."""

    hot: tuple[str, ...] = ("goal", "save", "penalty", "celebrating", "diving", "erupts")

    def score(self, shot: Cut, transcript: str, caption: str) -> float:
        words = f"{transcript} {caption}".lower().split()
        return min(1.0, sum(w in self.hot for w in words) / 3)


@dataclass(frozen=True)
class EdlEntry:
    shot: int
    src_in: float
    src_out: float
    score: float
    reason: str


@dataclass
class Plan:
    entries: list[EdlEntry]
    target_lufs: float

    @property
    def seconds(self) -> float:
        return round(sum(e.src_out - e.src_in for e in self.entries), 3)

    def record_points(self) -> list[float]:
        """Where cuts should appear in the output (cumulative entry lengths)."""
        pts, t = [], 0.0
        for e in self.entries[:-1]:
            t += e.src_out - e.src_in
            pts.append(round(t, 3))
        return pts


@dataclass
class Report:
    plan: Plan
    out: Path
    failures: list[str]
    trace: list[str] = field(default_factory=list)


def shots_from_cuts(cuts: Sequence[float], duration: float) -> list[Cut]:
    edges = [0.0, *cuts, duration]
    return [Cut(a, b) for a, b in zip(edges, edges[1:], strict=False) if b - a > 0.2]


def text_in(shot: Cut, segments: Sequence[Segment]) -> str:
    return " ".join(s.text for s in segments if s.start < shot.end and s.end > shot.start)


def plan_edl(
    shots: Sequence[Cut],
    scores: Sequence[float],
    budget_s: float,
    max_shot_s: float = 1.6,
    margin_s: float = 0.2,
    min_score: float = 0.3,
    target_lufs: float = -16.0,
) -> Plan:
    """Greedy by score under a duration budget, then put back in story (time) order.

    Entries are snapped to whole frames and start `margin_s` after the cut so a
    detector that is a frame late never leaks the previous shot into the reel."""
    snap = lambda t: round(round(t * FPS) / FPS, 3)  # noqa: E731
    chosen: list[EdlEntry] = []
    used = 0.0
    for i in sorted(range(len(shots)), key=lambda i: -scores[i]):
        if scores[i] < min_score:
            break
        s = shots[i]
        src_in = snap(s.start + margin_s)
        src_out = snap(min(s.end - margin_s, src_in + max_shot_s))
        length = src_out - src_in
        if length <= 0 or used + length > budget_s + 1e-6:
            continue
        chosen.append(EdlEntry(i, src_in, src_out, scores[i], f"score {scores[i]:.2f}"))
        used += length
    return Plan(sorted(chosen, key=lambda e: e.src_in), target_lufs)


def verify(out: Path, plan: Plan, tol_s: float = 0.1, tol_lu: float = 1.0) -> list[str]:
    """Objective checks against the plan: duration, streams, loudness, cut points."""
    fails = []
    p = probe(out)
    if abs(p.duration - plan.seconds) > tol_s:
        fails.append(f"duration {p.duration:.3f}s vs plan {plan.seconds:.3f}s")
    if (p.video_streams, p.audio_streams) != (1, 1):
        fails.append(f"streams v={p.video_streams} a={p.audio_streams}")
    lufs = loudness_lufs(out)
    if abs(lufs - plan.target_lufs) > tol_lu:
        fails.append(f"loudness {lufs:.1f} LUFS vs target {plan.target_lufs}")
    found = scene_cuts(out)
    want = plan.record_points()
    if len(found) != len(want) or any(
        abs(round(f * FPS) - round(w * FPS)) > 1 for f, w in zip(found, want, strict=False)
    ):
        fails.append(f"cut points {found} vs plan {want} (1-frame tolerance)")
    return fails


def run(
    src: Path,
    out: Path,
    transcriber: Transcriber,
    scorer: Scorer,
    captions: Sequence[str],
    budget_s: float = 4.0,
) -> Report:
    trace = []
    info = probe(src)
    trace.append(f"probe: {info.duration:.2f}s {info.width}x{info.height} @ {info.fps}fps")
    cuts = scene_cuts(src)
    shots = shots_from_cuts(cuts, info.duration)
    trace.append(f"scene_cuts: {cuts} -> {len(shots)} shots")
    segments = transcriber.transcribe(src)
    trace.append(f"transcribe: {len(segments)} segments")
    scores = [
        scorer.score(s, text_in(s, segments), captions[i] if i < len(captions) else "")
        for i, s in enumerate(shots)
    ]
    trace.append(f"score: {[round(x, 2) for x in scores]}")
    plan = plan_edl(shots, scores, budget_s)
    trace.append(f"plan: {[(e.shot, e.src_in, e.src_out) for e in plan.entries]}")
    render(src, [Cut(e.src_in, e.src_out) for e in plan.entries], out, plan.target_lufs)
    fails = verify(out, plan)
    trace.append("verify: ok" if not fails else f"verify: {fails}")
    return Report(plan, out, fails, trace)


def load_fixture() -> tuple[list[Shot], list[Segment], list[str]]:
    data = json.loads(FIXTURE.read_text())
    return (
        [Shot(**s) for s in data["shots"]],
        [Segment(**s) for s in data["transcript"]],
        data["captions"],
    )


def main() -> None:
    shots, segments, captions = load_fixture()
    with tempfile.TemporaryDirectory() as tmp:
        src = make_clip(Path(tmp) / "match.mp4", shots)
        rep = run(
            src, Path(tmp) / "reel.mp4", FixedTranscriber(segments), KeywordScorer(), captions
        )
        print("\n".join(rep.trace))
        print(json.dumps([asdict(e) for e in rep.plan.entries], indent=2))


if __name__ == "__main__":
    main()
