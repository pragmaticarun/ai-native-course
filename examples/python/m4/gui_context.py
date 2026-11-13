"""M4 worked example: GUI and on-device context.

(a) Prune an Android accessibility tree or an HTML DOM to interactive nodes,
    give each a STABLE id (set-of-marks), and compare token cost with the raw
    tree and with a screenshot.
(b) Downscale a screenshot to a model's image limits and map the model's
    coordinates back to device pixels.
(c) Fit a prompt plus history into a small on-device context window, using a
    running summary as memory.

Image token cost follows Anthropic's documented rule (checked 13 Nov 2026):
visual tokens = ceil(w/28) * ceil(h/28), with per-tier caps on long edge and
tokens (https://platform.claude.com/docs/en/build-with-claude/vision). Other
providers price images differently. Screenshots returned to Anthropic's
computer-use tool are rejected (not downscaled) when over the limit, so the
resize in (b) is your job.
"""

from __future__ import annotations

import hashlib
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser

from context_budget import approx_tokens

# ----------------------------------------------------------------------------- (a) pruning


@dataclass(frozen=True)
class Mark:
    id: str  # stable across screenshots: derived from identity, not list position
    role: str
    label: str
    center: tuple[int, int]


def stable_id(*identity: str) -> str:
    return hashlib.sha1("|".join(identity).encode()).hexdigest()[:4]


def prune_android(xml: str) -> list[Mark]:
    marks: list[Mark] = []
    for el in ET.fromstring(xml).iter("node"):
        clickable = el.get("clickable") == "true"
        editable = el.get("class", "").endswith("EditText")
        if not (clickable or editable):
            continue
        x1, y1, x2, y2 = (
            int(v) for v in el.get("bounds", "[0,0][0,0]").replace("][", ",").strip("[]").split(",")
        )
        label = el.get("text") or el.get("content-desc") or el.get("resource-id") or ""
        role = "input" if editable else "button"
        marks.append(
            Mark(
                stable_id(el.get("resource-id", ""), label, role),
                role,
                label,
                ((x1 + x2) // 2, (y1 + y2) // 2),
            )
        )
    return marks


class _DomPruner(HTMLParser):
    INTERACTIVE = {"a", "button", "input", "select", "textarea"}

    def __init__(self) -> None:
        super().__init__()
        self.marks: list[Mark] = []
        self._open: tuple[str, dict[str, str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag not in self.INTERACTIVE or "hidden" in a or a.get("type") == "hidden":
            return
        if tag == "input":
            label = a.get("aria-label") or a.get("placeholder") or a.get("name", "")
            self._add(tag, a, label)
        else:
            self._open = (tag, a)

    def handle_data(self, data: str) -> None:
        if self._open and data.strip():
            tag, a = self._open
            self._add(tag, a, a.get("aria-label") or data.strip())
            self._open = None

    def _add(self, tag: str, a: dict[str, str], label: str) -> None:
        role = {"a": "link", "button": "button"}.get(tag, "input")
        self.marks.append(Mark(stable_id(a.get("id", ""), label, role), role, label, (0, 0)))


def prune_dom(html: str) -> list[Mark]:
    p = _DomPruner()
    p.feed(html)
    return p.marks


def render_marks(marks: list[Mark]) -> str:
    return "\n".join(f"[{m.id}] {m.role} {m.label!r}" for m in marks)


# ----------------------------------------------------------------------------- (b) screenshots

STANDARD = (1568, 1568)  # (max long edge px, max visual tokens): Anthropic standard tier
HIGH_RES = (2576, 4784)  # Anthropic high-resolution tier


def visual_tokens(w: int, h: int) -> int:
    return math.ceil(w / 28) * math.ceil(h / 28)


def fit_screenshot(w: int, h: int, tier: tuple[int, int] = STANDARD) -> tuple[int, int, float]:
    """Largest aspect-preserving size within the tier's long-edge and token caps.

    An approximation of the documented rule; Anthropic's docs link a reference
    implementation if you need their exact numbers.
    """
    max_edge, max_tokens = tier
    scale = min(1.0, max_edge / max(w, h))
    while visual_tokens(round(w * scale), round(h * scale)) > max_tokens:
        scale *= 0.995
    return round(w * scale), round(h * scale), scale


def to_device(x: int, y: int, scale: float) -> tuple[int, int]:
    """Model coordinates (on the downscaled image) -> device pixels."""
    return round(x / scale), round(y / scale)


# ----------------------------------------------------------------------------- (c) small windows

GEMINI_NANO_INPUT = 4000  # ML Kit Prompt API's documented ~4k-token input guidance
LITERT_LM_A73 = 2048  # the context we configure for Gemma 3 1B on the A73 (our choice)


def fit_small_window(
    system: str,
    summary: str,
    turns: list[str],
    question: str,
    window: int,
    reserve_output: int = 256,
) -> tuple[str, int]:
    """Always keep system + summary + question; add newest turns while they fit."""
    budget = window - reserve_output
    fixed = [system, f"Memory: {summary}" if summary else "", question]
    used = sum(approx_tokens(p) for p in fixed)
    if used > budget:
        raise ValueError("system + summary + question alone exceed the window; shorten the summary")
    kept: list[str] = []
    for t in reversed(turns):
        if used + approx_tokens(t) > budget:
            break
        kept.insert(0, t)
        used += approx_tokens(t)
    prompt = "\n".join(p for p in [fixed[0], fixed[1], *kept, fixed[2]] if p)
    return prompt, len(turns) - len(kept)


if __name__ == "__main__":
    from pathlib import Path

    xml = (Path(__file__).parent.parent / "m3" / "fixtures" / "login_screen.xml").read_text()
    marks = prune_android(xml)
    print(render_marks(marks))
    print(
        "raw xml tokens:", approx_tokens(xml), "marks tokens:", approx_tokens(render_marks(marks))
    )
    w, h, s = fit_screenshot(1080, 2400)  # Galaxy A73 screen is 1080x2400
    print(f"A73 screenshot -> {w}x{h} ({visual_tokens(w, h)} visual tokens), scale {s:.3f}")
