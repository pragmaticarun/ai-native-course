"""P3 milestone 6: objective evals for the agent's output (no judge model needed).

For an edit with EDL `cuts` and a loudness target, the output must have:
* the right duration (sum of the cuts, ±0.1 s) and both a video and an audio stream;
* integrated loudness within ±1 LU of the target, measured independently with ffmpeg's
  `ebur128` (the server used `loudnorm`; two meters, so we're not grading our own homework);
* scene cuts at the EDL boundaries, within one frame.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

_EX = Path(__file__).resolve().parents[3] / "examples" / "python"
if str(_EX / "m14") not in sys.path:
    sys.path.append(str(_EX / "m14"))

import media_tools as mt  # noqa: E402

FRAME = 1 / 25


@dataclass
class Check:
    duration_s: float
    lufs: float
    cuts: list[float]
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def check_output(path: Path, edl: list[dict[str, float]], target_lufs: float) -> Check:
    p = mt.probe(path)
    lufs = mt.loudness_lufs(path)
    cuts = mt.scene_cuts(path)
    c = Check(p.duration, lufs, cuts)
    want = sum(e["end"] - e["start"] for e in edl)
    if abs(p.duration - want) > 0.1:
        c.problems.append(f"duration {p.duration} != {want:.3f}")
    if not (p.video_streams and p.audio_streams):
        c.problems.append("missing a video or audio stream")
    if abs(lufs - target_lufs) > 1.0:
        c.problems.append(f"loudness {lufs} LUFS not within 1 LU of {target_lufs}")
    boundaries, acc = [], 0.0
    for e in edl[:-1]:
        acc += e["end"] - e["start"]
        boundaries.append(acc)
    for b in boundaries:
        if not any(abs(b - x) <= FRAME + 1e-6 for x in cuts):
            c.problems.append(f"no scene cut within one frame of {b:.3f}s")
    return c
