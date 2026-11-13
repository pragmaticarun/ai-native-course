"""L2 worked example (multimodal): send a video frame to a model, on a pixel budget.

Steps: grab a frame with ffmpeg -> downscale so the long edge fits a budget ->
send it -> map coordinates the model returns back to original pixels (this
mapping comes back in M15 for GUI agents).

Token cost per image differs by provider and changes over time, so we compute
pixels and scale factors only; check your provider's docs for its image pricing.
"""

from __future__ import annotations

import base64
import shutil
import subprocess
from pathlib import Path


def ffmpeg_frame_cmd(video: str, at_seconds: float, out_png: str) -> list[str]:
    """ffmpeg command that writes one frame at `at_seconds` as PNG."""
    return [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        f"{at_seconds:.3f}",
        "-i",
        video,
        "-frames:v",
        "1",
        out_png,
    ]


def fit_long_edge(width: int, height: int, max_long_edge: int) -> tuple[int, int, float]:
    """New (w, h) whose long edge is <= max_long_edge, plus the scale factor used."""
    scale = min(1.0, max_long_edge / max(width, height))
    return max(1, round(width * scale)), max(1, round(height * scale)), scale


def to_original(x: int, y: int, scale: float) -> tuple[int, int]:
    """Map a coordinate in the downscaled image back to original pixels."""
    return round(x / scale), round(y / scale)


def image_part(png_bytes: bytes) -> dict[str, str]:
    """A provider-neutral image payload; adapters convert it to each vendor's format."""
    return {
        "type": "image",
        "media_type": "image/png",
        "data": base64.b64encode(png_bytes).decode(),
    }


def grab_frame(video: str, at_seconds: float, out_png: str) -> Path:
    """Runs ffmpeg (must be installed). Not run in CI; tested locally only."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH")
    subprocess.run(ffmpeg_frame_cmd(video, at_seconds, out_png), check=True)
    return Path(out_png)


if __name__ == "__main__":
    w, h, s = fit_long_edge(3840, 2160, 1280)
    print(f"4K frame -> {w}x{h} (scale {s:.3f}); {3840 * 2160 / (w * h):.1f}x fewer pixels")
    print("model clicked (640, 360) in the small image ->", to_original(640, 360, s), "in 4K")
