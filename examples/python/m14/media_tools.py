"""M14 L14.2: typed ffmpeg/ffprobe tools for an agent (never raw shell strings).

Every function builds an argv list itself, takes paths that must resolve inside a
sandbox root, and returns parsed observations (dataclasses), not raw stderr. The
model picks *which* tool and *which* numbers; it never writes ffmpeg flags.

Tested against the ffmpeg on PATH (CI: Ubuntu's package; the box: 7.1.5) using
clips generated with lavfi, so no media files are checked in.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

TIMEOUT_S = 60


class MediaToolError(RuntimeError):
    pass


def have_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def resolve_in_root(root: Path, rel: str) -> Path:
    """Reject protocols (`http:`, `concat:`, `pipe:`...), absolute paths and `..` escapes."""
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", rel):
        raise MediaToolError(f"protocol-style path refused: {rel!r}")
    p = (root / rel).resolve()
    if not p.is_relative_to(root.resolve()):
        raise MediaToolError(f"path escapes sandbox: {rel!r}")
    return p


def _run(argv: Sequence[str], timeout: float = TIMEOUT_S) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(list(argv), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise MediaToolError(f"timed out after {timeout}s: {argv[0]}") from e
    if proc.returncode != 0:
        raise MediaToolError(proc.stderr.strip().splitlines()[-1] if proc.stderr else "failed")
    return proc


# ---------- fixtures: deterministic clips from lavfi ----------


@dataclass(frozen=True)
class Shot:
    color: str
    seconds: float
    tone_hz: int | None  # None = silence


def make_clip(out: Path, shots: Sequence[Shot], size: str = "320x240", fps: int = 25) -> Path:
    """Concatenate solid-colour shots, each with a sine tone or silence, into one MP4."""
    args: list[str] = ["ffmpeg", "-y", "-loglevel", "error"]
    for s in shots:
        args += ["-f", "lavfi", "-i", f"color=c={s.color}:s={size}:r={fps}:d={s.seconds}"]
        audio = (
            f"sine=frequency={s.tone_hz}:sample_rate=48000:duration={s.seconds}"
            if s.tone_hz
            else f"anullsrc=r=48000:cl=mono,atrim=duration={s.seconds}"
        )
        args += ["-f", "lavfi", "-i", audio]
    pairs = "".join(f"[{2 * i}:v][{2 * i + 1}:a]" for i in range(len(shots)))
    args += [
        "-filter_complex",
        f"{pairs}concat=n={len(shots)}:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", str(fps),
        "-c:a", "aac", "-ac", "1",
        str(out),
    ]  # fmt: skip
    _run(args)
    return out


# ---------- observations ----------


@dataclass(frozen=True)
class Probe:
    duration: float
    width: int | None
    height: int | None
    fps: float | None
    audio_streams: int
    video_streams: int
    sample_rate: int | None


def parse_ffprobe(text: str) -> Probe:
    data = json.loads(text)
    streams = data.get("streams", [])
    v = next((s for s in streams if s["codec_type"] == "video"), None)
    a = next((s for s in streams if s["codec_type"] == "audio"), None)
    fps = None
    if v and v.get("avg_frame_rate", "0/0") != "0/0":
        num, den = v["avg_frame_rate"].split("/")
        fps = int(num) / int(den)
    return Probe(
        duration=float(data["format"]["duration"]),
        width=v and int(v["width"]),
        height=v and int(v["height"]),
        fps=fps,
        audio_streams=sum(1 for s in streams if s["codec_type"] == "audio"),
        video_streams=sum(1 for s in streams if s["codec_type"] == "video"),
        sample_rate=int(a["sample_rate"]) if a else None,
    )


def probe(path: Path) -> Probe:
    out = _run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams",
         str(path)]
    ).stdout  # fmt: skip
    return parse_ffprobe(out)


def scene_cuts(path: Path, threshold: float = 0.3) -> list[float]:
    """Timestamps where ffmpeg's scene score exceeds `threshold` (select + showinfo)."""
    proc = _run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-an",
         "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"]
    )  # fmt: skip
    return [round(float(t), 3) for t in re.findall(r"pts_time:([\d.]+)", proc.stderr)]


def silences(path: Path, noise_db: float = -40.0, min_s: float = 0.3) -> list[tuple[float, float]]:
    proc = _run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn",
         "-af", f"silencedetect=noise={noise_db}dB:d={min_s}", "-f", "null", "-"]
    )  # fmt: skip
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", proc.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", proc.stderr)]
    return [(round(s, 3), round(e, 3)) for s, e in zip(starts, ends, strict=False)]


def loudness_lufs(path: Path) -> float:
    """Integrated loudness from the ebur128 summary block ("I: -23.0 LUFS")."""
    proc = _run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn",
         "-af", "ebur128", "-f", "null", "-"]
    )  # fmt: skip
    summary = proc.stderr.rsplit("Summary:", 1)[-1]
    m = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summary)
    if not m:
        raise MediaToolError("ebur128 summary not found")
    return float(m.group(1))


def thumbnail(path: Path, out: Path, at: float) -> Path:
    _run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at:.3f}", "-i", str(path),
          "-frames:v", "1", str(out)])  # fmt: skip
    return out


def best_thumbnail(path: Path, out: Path, window: int = 25) -> Path:
    """ffmpeg's `thumbnail` filter: the most representative frame per `window` frames."""
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
          "-vf", f"thumbnail={window}", "-frames:v", "1", str(out)])  # fmt: skip
    return out


# ---------- edits: dry run first, then render ----------


@dataclass(frozen=True)
class Cut:
    start: float
    end: float

    @property
    def seconds(self) -> float:
        return round(self.end - self.start, 3)


def concat_argv(
    src: Path, cuts: Sequence[Cut], out: Path | None, audio_filter: str | None
) -> list[str]:
    """Build (but do not run) the argv: trim/atrim per cut -> concat -> optional audio filter.

    `out=None` renders to the null muxer (used for the loudness measuring pass)."""
    if not cuts:
        raise MediaToolError("empty edit list")
    parts = []
    for i, c in enumerate(cuts):
        if c.end <= c.start:
            raise MediaToolError(f"cut {i} has end <= start")
        parts.append(
            f"[0:v]trim=start={c.start}:end={c.end},setpts=PTS-STARTPTS[v{i}];"
            f"[0:a]atrim=start={c.start}:end={c.end},asetpts=PTS-STARTPTS[a{i}]"
        )
    pairs = "".join(f"[v{i}][a{i}]" for i in range(len(cuts)))
    graph = ";".join(parts) + f";{pairs}concat=n={len(cuts)}:v=1:a=1[v][a0]"
    graph += f";[a0]{audio_filter or 'anull'}[a]"
    head = ["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", str(src),
            "-filter_complex", graph, "-map", "[v]", "-map", "[a]"]  # fmt: skip
    if out is None:
        return head + ["-f", "null", "-"]
    return head + ["-loglevel", "error", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-ar", "48000", str(out)]  # fmt: skip


def measure_loudnorm(src: Path, cuts: Sequence[Cut], target: float) -> dict[str, float]:
    """Pass 1 of two-pass loudnorm on the edited audio: input_i/tp/lra/thresh, target_offset."""
    proc = _run(
        concat_argv(src, cuts, None, f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json")
    )
    blob = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, re.S)
    if not blob:
        raise MediaToolError("loudnorm JSON not found")
    return {k: float(v) for k, v in json.loads(blob.group(0)).items() if k != "normalization_type"}


def render(src: Path, cuts: Sequence[Cut], out: Path, target_lufs: float = -16.0) -> Path:
    """Two-pass loudnorm: measure the edit, then render it once with linear normalisation."""
    m = measure_loudnorm(src, cuts, target_lufs)
    ln = (
        f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:measured_I={m['input_i']}"
        f":measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
        f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
    )
    _run(concat_argv(src, cuts, out, ln))
    return out


def frame_at(path: Path, t: float, fps: int = 25) -> int:
    """Frame index for a timestamp (what 'frame-accurate' means in tests)."""
    return round(t * fps)
