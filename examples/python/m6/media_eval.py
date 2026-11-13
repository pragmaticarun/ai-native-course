"""M6 worked example: objective graders for a media agent.

* duration and streams via `ffprobe -show_format -show_streams -of json`;
* integrated loudness via ffmpeg's `loudnorm` filter (`print_format=json`, which
  prints `input_i` in LUFS among other fields);
* word error rate (WER) for transcripts: word-level edit distance / reference words.

Uses whatever ffmpeg/ffprobe is on PATH (CI installs Ubuntu's package; the course's
pinned FFmpeg 9.0.2 container arrives with M14). Tests generate their own audio.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


def have_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def make_tone(out: Path, seconds: float = 3.0, volume_db: float = -20.0, rate: int = 48000) -> Path:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=1000:duration={seconds}:sample_rate={rate}",
            "-af",
            f"volume={volume_db}dB",
            "-ac",
            "2",
            str(out),
        ],
        check=True,
    )
    return out


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    data = json.loads(out)
    audio = [s for s in data["streams"] if s["codec_type"] == "audio"]
    return {
        "duration": float(data["format"]["duration"]),
        "audio_streams": len(audio),
        "video_streams": sum(1 for s in data["streams"] if s["codec_type"] == "video"),
        "sample_rate": int(audio[0]["sample_rate"]) if audio else None,
        "channels": int(audio[0]["channels"]) if audio else None,
    }


def integrated_loudness(path: Path) -> float:
    proc = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "loudnorm=print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    blob = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, re.S)
    if not blob:
        raise RuntimeError("loudnorm JSON not found in ffmpeg output")
    return float(json.loads(blob.group(0))["input_i"])


def wer(reference: str, hypothesis: str) -> float:
    norm = lambda s: re.sub(r"[^\w\s']", "", s.lower()).split()  # noqa: E731
    r, h = norm(reference), norm(hypothesis)
    if not r:
        return 0.0 if not h else 1.0
    prev = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        cur = [i] + [0] * len(h)
        for j, hw in enumerate(h, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rw != hw))
        prev = cur
    return prev[-1] / len(r)


def grade_media(
    path: Path, expect_seconds: float, target_lufs: float, tol_s: float = 0.1, tol_lu: float = 1.5
) -> list[str]:
    """Return a list of failures (empty = pass)."""
    info = probe(path)
    fails = []
    if abs(info["duration"] - expect_seconds) > tol_s:
        fails.append(f"duration {info['duration']:.2f}s != {expect_seconds}s")
    if info["audio_streams"] != 1:
        fails.append(f"expected 1 audio stream, got {info['audio_streams']}")
    lufs = integrated_loudness(path)
    if abs(lufs - target_lufs) > tol_lu:
        fails.append(f"loudness {lufs:.1f} LUFS not within {tol_lu} LU of {target_lufs}")
    return fails
