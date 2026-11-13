"""M14 L14.6: evaluating media agents beyond objective metrics.

* `judge_caption`: an LLM-judge rubric (faithful / specific / no invented entities), with
  the judge passed in as a function so CI uses a mock and you can swap in a real model.
* `privacy_findings`: a checklist pass over an output manifest for faces, voices and screen
  recordings: what needs consent, blurring, or must not leave the device.
Objective metrics (duration, streams, LUFS, cut points, WER) live in highlight_reel.verify
and speech_pipeline; this file is the subjective and policy half.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

RUBRIC = """Score the caption against the reference facts. Reply with JSON only:
{"faithful": 0|1, "specific": 0|1, "invented_entities": [..], "reason": "..."}
faithful = says nothing the facts contradict; specific = names the main action;
invented_entities = people/places/brands not in the facts."""


@dataclass(frozen=True)
class Verdict:
    faithful: bool
    specific: bool
    invented: list[str]
    reason: str

    @property
    def passed(self) -> bool:
        return self.faithful and self.specific and not self.invented


def judge_caption(caption: str, facts: str, judge: Callable[[str], str]) -> Verdict:
    raw = judge(f"{RUBRIC}\n\nFACTS: {facts}\nCAPTION: {caption}")
    try:
        d = json.loads(raw)
        return Verdict(bool(d["faithful"]), bool(d["specific"]), list(d["invented_entities"]),
                       str(d.get("reason", "")))  # fmt: skip
    except (json.JSONDecodeError, KeyError, TypeError):
        return Verdict(False, False, [], f"unparseable judge output: {raw[:60]!r}")


def mock_judge(prompt: str) -> str:
    """Deterministic stand-in: flags capitalised words in the caption that the facts lack."""
    facts = prompt.split("FACTS:", 1)[1].split("CAPTION:", 1)[0].lower()
    cap = prompt.split("CAPTION:", 1)[1].strip()
    invented = [
        w.strip(".,") for w in cap.split() if w[:1].isupper() and w.lower().strip(".,") not in facts
    ]
    specific = any(w in cap.lower() for w in facts.split() if len(w) > 4)
    return json.dumps({"faithful": int(not invented), "specific": int(specific),
                       "invented_entities": invented, "reason": "mock"})  # fmt: skip


def privacy_findings(manifest: dict) -> list[str]:
    """Policy checks over what an agent produced. Returns findings to fix before sharing."""
    out = []
    if manifest.get("faces_detected", 0) and not manifest.get("faces_blurred"):
        out.append("faces present and not blurred: blur or get consent before sharing")
    if manifest.get("voices") and not manifest.get("voice_consent"):
        out.append("identifiable voices without recorded consent")
    if manifest.get("source") == "screen_recording" and manifest.get("ocr_text"):
        secrets = [
            w
            for w in manifest["ocr_text"]
            if any(k in w.lower() for k in ("password", "token", "otp"))
        ]
        if secrets:
            out.append(f"screen recording shows sensitive text: {secrets}")
    if manifest.get("upload_to_cloud") and manifest.get("privacy_class") == "on_device_only":
        out.append("privacy class forbids cloud upload")
    return out
