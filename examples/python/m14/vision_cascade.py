"""M14 L14.1 + L14.5: frame sampling, cost accounting, and "cheap filter first, VLM second".

Real: frame statistics come from ffmpeg (`signalstats` YAVG per frame) and scene cuts from
media_tools. Mock: the VLM (`caption`) is a function you pass in. Costs use **your**
per-frame token count and price as parameters; we do not quote any vendor's numbers.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media_tools import scene_cuts  # noqa: E402


def uniform_times(duration: float, every_s: float) -> list[float]:
    n = int(duration / every_s)
    return [round(i * every_s, 3) for i in range(n + 1) if i * every_s < duration]


def scene_times(cuts: Sequence[float], duration: float, offset_s: float = 0.2) -> list[float]:
    """One keyframe per shot, slightly after the cut (avoids transition frames)."""
    return [round(t + offset_s, 3) for t in [0.0, *cuts] if t + offset_s < duration]


def budgeted(times: Sequence[float], max_frames: int) -> list[float]:
    """Thin a candidate list evenly to fit a frame budget."""
    if len(times) <= max_frames:
        return list(times)
    step = len(times) / max_frames
    return [times[int(i * step)] for i in range(max_frames)]


@dataclass(frozen=True)
class Cost:
    frames: int
    tokens: int
    dollars: float
    seconds: float


def cost(frames: int, tokens_per_frame: int, usd_per_mtok: float, s_per_call: float) -> Cost:
    tok = frames * tokens_per_frame
    return Cost(frames, tok, round(tok * usd_per_mtok / 1e6, 6), round(frames * s_per_call, 3))


def luma_per_frame(path: Path) -> list[tuple[float, float]]:
    """(pts_time, YAVG) for every frame, via ffmpeg signalstats + metadata=print."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-an",
         "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"],
        capture_output=True, text=True, check=True, timeout=60,
    )  # fmt: skip
    times = [float(t) for t in re.findall(r"pts_time:([\d.]+)", proc.stderr)]
    yavg = [float(v) for v in re.findall(r"YAVG=([\d.]+)", proc.stderr)]
    return list(zip(times, yavg, strict=False))


@dataclass
class CascadeResult:
    candidates: int
    sent_to_vlm: int
    captions: dict[float, str]


def cascade(
    path: Path,
    duration: float,
    caption: Callable[[float], str],
    min_luma: float = 20.0,
) -> CascadeResult:
    """Stage 1 (cheap): scene keyframes, drop near-black frames. Stage 2: VLM on the rest."""
    keys = scene_times(scene_cuts(path), duration)
    luma = luma_per_frame(path)

    def bright(t: float) -> bool:
        near = min(luma, key=lambda p: abs(p[0] - t))
        return near[1] >= min_luma

    keep = [t for t in keys if bright(t)]
    return CascadeResult(len(keys), len(keep), {t: caption(t) for t in keep})
