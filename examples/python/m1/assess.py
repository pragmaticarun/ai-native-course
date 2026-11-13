"""M1 worked example: score a self-assessment worksheet and draw a radar chart.

The gating rule below (which DORA capabilities must be >= 2 to *sustain* a
Shapiro level) is the course's own teaching synthesis. It is not from Shapiro
or DORA, and the lesson says so.

Run: uv run python ../examples/python/m1/assess.py ../examples/python/m1/worksheet.example.yaml
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

CAPABILITIES = (
    "clear_ai_stance",
    "healthy_data_ecosystems",
    "ai_accessible_internal_data",
    "strong_version_control",
    "small_batches",
    "user_centric_focus",
    "quality_internal_platforms",
)

# Course synthesis: capabilities that must score >= 2 before a level is "sustainable".
GATES: dict[int, tuple[str, ...]] = {
    2: ("clear_ai_stance",),
    3: ("clear_ai_stance", "strong_version_control", "small_batches"),
    4: (
        "clear_ai_stance",
        "strong_version_control",
        "small_batches",
        "quality_internal_platforms",
        "ai_accessible_internal_data",
    ),
    5: CAPABILITIES,
}


class Worksheet(BaseModel):
    team: str
    workflow_level: int = Field(ge=0, le=5)
    capabilities: dict[str, int]

    def model_post_init(self, _context: object) -> None:
        missing = set(CAPABILITIES) - set(self.capabilities)
        if missing:
            raise ValueError(f"missing capabilities: {sorted(missing)}")
        if any(not 0 <= v <= 3 for v in self.capabilities.values()):
            raise ValueError("capability scores must be 0..3")


def sustainable_level(ws: Worksheet) -> int:
    """Highest level whose prerequisite capabilities are all >= 2."""
    level = 1  # L0/L1 need no prerequisites in our synthesis
    for lvl in sorted(GATES):
        if all(ws.capabilities[c] >= 2 for c in GATES[lvl]):
            level = lvl
        else:
            break
    return level


def gaps_for(ws: Worksheet, target: int) -> list[str]:
    return [c for c in GATES.get(target, ()) if ws.capabilities[c] < 2]


def radar_svg(scores: dict[str, int], size: int = 320) -> str:
    """A dependency-free SVG radar chart (0..3 scale)."""
    cx = cy = size / 2
    radius = size / 2 - 40
    n = len(CAPABILITIES)

    def point(i: int, value: float) -> tuple[float, float]:
        angle = -math.pi / 2 + 2 * math.pi * i / n
        r = radius * value / 3
        return cx + r * math.cos(angle), cy + r * math.sin(angle)

    rings = "".join(
        '<polygon fill="none" stroke="#ccc" points="'
        + " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, ring) for i in range(n)))
        + '"/>'
        for ring in (1, 2, 3)
    )
    shape = " ".join(
        f"{x:.1f},{y:.1f}" for x, y in (point(i, scores[c]) for i, c in enumerate(CAPABILITIES))
    )
    labels = "".join(
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="9" text-anchor="middle">{c}</text>'
        for (x, y), c in ((point(i, 3.45), c) for i, c in enumerate(CAPABILITIES))
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">{rings}'
        f'<polygon fill="rgba(80,120,220,0.35)" stroke="#3060c0" points="{shape}"/>'
        f"{labels}</svg>"
    )


def report(ws: Worksheet) -> str:
    sus = sustainable_level(ws)
    lines = [
        f"Team: {ws.team}",
        f"Observed workflow level: L{ws.workflow_level}",
        f"Sustainable level (course synthesis): L{sus}",
    ]
    if ws.workflow_level > sus:
        lines.append(
            f"Warning: working above what your capabilities support; "
            f"fix {gaps_for(ws, ws.workflow_level)} first."
        )
    nxt = min(ws.workflow_level + 1, 5)
    lines.append(f"To reach L{nxt}, raise to >= 2: {gaps_for(ws, nxt) or 'nothing, go'}")
    return "\n".join(lines)


def load(path: str | Path) -> Worksheet:
    return Worksheet.model_validate(yaml.safe_load(Path(path).read_text()))


if __name__ == "__main__":
    ws = load(
        sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("worksheet.example.yaml")
    )
    print(report(ws))
    Path("radar.svg").write_text(radar_svg(ws.capabilities))
    print("wrote radar.svg")
