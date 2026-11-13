"""P3 kit (provided): golden media fixtures generated with ffmpeg's lavfi sources.

`make_media_root(tmp)` writes:
* `match.mp4`: M14's synthetic match (5 solid-colour shots with tones; the black shot is
  silent), 10.52 s, scene cuts near 2.0 / 3.52 / 6.04 / 8.04 s, silence 2.0-3.52 s;
* `a.mp4`, `b.mp4`: two short clips for `concat`;
* `tone.wav`: a 2 s 440 Hz sine.

Generated, not CC-licensed recordings (see the M14 deviation note).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_EX = Path(__file__).resolve().parents[3] / "examples" / "python"
for _p in sorted(_EX.glob("m*")):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

import media_tools as mt  # noqa: E402

MATCH = json.loads((_EX / "m14" / "fixtures" / "highlight.json").read_text())
MATCH_DURATION = 10.52
MATCH_CUTS = (2.0, 3.52, 6.04, 8.04)
MATCH_SILENCE = (2.0, 3.52)


def make_media_root(tmp: Path) -> Path:
    root = tmp / "media"
    root.mkdir(parents=True, exist_ok=True)
    mt.make_clip(root / "match.mp4", [mt.Shot(**s) for s in MATCH["shots"]])
    mt.make_clip(root / "a.mp4", [mt.Shot("red", 1.0, 440), mt.Shot("blue", 1.0, 660)])
    mt.make_clip(root / "b.mp4", [mt.Shot("white", 1.2, 880)])
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-ar", "48000", str(root / "tone.wav")],
        check=True,
    )  # fmt: skip
    return root
