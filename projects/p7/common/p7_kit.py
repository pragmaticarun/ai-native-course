"""P7 kit (provided): ten generated "talk" recordings with reference chapters and
transcripts, real signal tools (keyframe colour, audio level) and mock models.

What's real and what's mocked:
* real (ffmpeg): the recordings, probing, scene and silence detection, keyframe colour
  (a frame scaled to 1x1 pixel), per-segment loudness, the highlight reel and its checks;
* mocked: ASR (returns the reference words with deterministic errors at a profile's rate),
  the summariser (a template; the small local model sometimes invents a brand name) and the
  summary judge (M14's rubric judge with its mock).
The two profiles' cost and latency figures are **placeholders** chosen for the exercise,
not vendor prices or measured speeds. The point is the comparison machinery.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
_EX = HERE.parents[2] / "examples" / "python"
for _p in sorted(_EX.glob("m*")):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

import media_tools as mt  # noqa: E402

RECORDINGS: list[dict[str, Any]] = json.loads((HERE / "recordings.json").read_text())
BY_ID = {r["id"]: r for r in RECORDINGS}
FPS = 25
PALETTE = {
    "red": (255, 0, 0),
    "blue": (0, 0, 255),
    "green": (0, 128, 0),
    "yellow": (255, 255, 0),
    "purple": (128, 0, 128),
    "orange": (255, 165, 0),
    "white": (255, 255, 255),
    "cyan": (0, 255, 255),
    "black": (0, 0, 0),
}


def make_recordings(root: Path, ids: list[str] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for rec in RECORDINGS:
        if ids is None or rec["id"] in ids:
            out = root / f"{rec['id']}.mp4"
            if not out.exists():
                shots = [mt.Shot(s["color"], s["seconds"], s["tone_hz"]) for s in rec["shots"]]
                mt.make_clip(out, shots, size="160x120", fps=FPS)
    return root


def reference_chapters(rec_id: str) -> list[dict[str, Any]]:
    """Chapters = non-pause shots, with start/end times."""
    out, t = [], 0.0
    for s in BY_ID[rec_id]["shots"]:
        if not s.get("pause"):
            out.append(
                {
                    "start": round(t, 3),
                    "end": round(t + s["seconds"], 3),
                    "title": s["title"],
                    "transcript": s["transcript"],
                    "color": s["color"],
                }
            )
        t += s["seconds"]
    return out


def keyframe_color(path: Path, at: float) -> str:
    """Average colour of the frame at `at` (scaled to 1x1), named by the nearest palette entry."""
    raw = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{at:.3f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=1:1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        capture_output=True,
        check=True,
        timeout=60,
    ).stdout[:3]
    rgb = tuple(raw)
    return min(
        PALETTE, key=lambda n: sum((a - b) ** 2 for a, b in zip(PALETTE[n], rgb, strict=True))
    )


def segment_level_db(path: Path, start: float, end: float) -> float:
    """Mean volume (dBFS) of [start, end) with ffmpeg volumedetect; -91 means digital silence."""
    p = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{end - start:.3f}",
            "-i",
            str(path),
            "-vn",
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    for line in p.stderr.splitlines():
        if "mean_volume:" in line:
            return float(line.split("mean_volume:")[1].split()[0])
    return -91.0


# --------------------------------------------------------------------------- profiles
@dataclass(frozen=True)
class Profile:
    name: str
    asr_error_every: int  # mock ASR swaps every Nth word
    summary_invents: bool  # mock small summariser sometimes adds a brand name
    usd_per_media_hour: float  # PLACEHOLDER, not a vendor price
    seconds_per_media_second: float  # PLACEHOLDER, simulated processing speed
    note: str


PROFILES = {
    "local": Profile(
        "local", 7, True, 0.0, 0.9, "llama.cpp mtmd + whisper.cpp on the laptop (simulated)"
    ),
    "cloud": Profile(
        "cloud",
        19,
        False,
        1.20,
        0.15,
        "a hosted ASR + multimodal model (simulated, placeholder price)",
    ),
}


class TransientASRError(RuntimeError):
    """The ASR backend hiccuped. Retryable."""


@dataclass
class MockASR:
    """Returns the reference words for the chapter that overlaps [start, end) most, with
    every Nth word replaced (a crude stand-in for recognition errors)."""

    profile: Profile
    fail_first: set[str] = field(default_factory=set)  # segment keys that fail once
    calls: list[str] = field(default_factory=list)
    active: int = 0
    peak: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def transcribe(self, rec_id: str, start: float, end: float) -> str:
        key = f"{rec_id}@{start:.2f}"
        with self._lock:
            self.calls.append(key)
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            import time

            time.sleep(0.02)  # let parallel workers overlap so the concurrency limit matters
            if key in self.fail_first and self.calls.count(key) == 1:
                raise TransientASRError(key)
            best = max(
                reference_chapters(rec_id),
                key=lambda c: min(end, c["end"]) - max(start, c["start"]),
            )
            if min(end, best["end"]) - max(start, best["start"]) <= 0:
                return ""
            words = best["transcript"].split()
            n = self.profile.asr_error_every
            return " ".join("uh" if (i + 3) % n == 0 else w for i, w in enumerate(words))
        finally:
            with self._lock:
                self.active -= 1


def mock_summarise(profile: Profile, rec_id: str, chapters: list[dict[str, Any]]) -> str:
    titles = ", ".join(c["title"].lower() for c in chapters)
    text = f"A talk on {BY_ID[rec_id]['title'].lower()} covering {titles}."
    if profile.summary_invents and int(rec_id[-2:]) % 4 == 1:
        text += " Sponsored by Acme."  # the failure mode the judge has to catch
    return text


def mock_title(transcript: str) -> str:
    """Mock LLM chapter title: the topic phrase of the (possibly misrecognised) transcript."""
    words = transcript.split()
    if "about" in words:
        a = words.index("about") + 1
        rest = words[a:]
        b = rest.index("for") if "for" in rest else min(4, len(rest))
        if b:
            return " ".join(rest[:b]).capitalize()
    return " ".join(words[:4]).capitalize() or "Untitled"


def p3_server_dir() -> Path:
    """The P3 media-toolkit server (reference solution), used for the highlight reel."""
    return HERE.parents[1] / "p3" / "solution"
