"""M6 worked example: an on-device eval across a model ladder and runtimes.

The harness scores a golden-prompt suite (quality + tool-call accuracy) and
aggregates latency: time to first token (TTFT), decode tokens/s, peak memory.

STATUS: the harness logic is tested against `fixtures/ondevice_runs.json`, a
SYNTHETIC fixture with hand-typed numbers. Nothing here has been run on the
Galaxy A73 (or any device) yet; the planned ladder is FunctionGemma 270M,
Gemma 3 1B and Gemma 4 E2B on LiteRT-LM CPU / llama.cpp CPU (SYLLABUS.md M6).

Gemini Nano version drift: ML Kit lets you read the on-device base model name
(`getBaseModelName()` per the ML Kit docs; the A73 can't run Nano). The drift
check here compares recorded fixture names and flags when the same golden suite
must be re-baselined because the model underneath changed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median

FIXTURE = Path(__file__).parent / "fixtures" / "ondevice_runs.json"


@dataclass
class LadderRow:
    model: str
    runtime: str
    quality: float
    tool_accuracy: float
    ttft_ms_p50: float
    tokens_per_s: float
    peak_mb: int


def score_output(golden: dict, out: dict) -> tuple[bool | None, bool | None]:
    """(text_ok, tool_ok); None means 'not applicable to this prompt'."""
    if "expect_tool" in golden:
        ok = out.get("tool") == golden["expect_tool"] and out.get("args") == golden["expect_args"]
        return None, ok
    return golden["expect_text"].lower() in out.get("text", "").lower(), None


def evaluate_run(golden: list[dict], run: dict) -> LadderRow:
    text_scores, tool_scores = [], []
    for g in golden:
        t, k = score_output(g, run["outputs"].get(g["id"], {}))
        if t is not None:
            text_scores.append(t)
        if k is not None:
            tool_scores.append(k)
    tps = [tok / (ms / 1000) for tok, ms in zip(run["tokens"], run["decode_ms"], strict=True)]
    return LadderRow(
        run["model"],
        run["runtime"],
        float(mean(text_scores)) if text_scores else 0.0,
        float(mean(tool_scores)) if tool_scores else 0.0,
        median(run["ttft_ms"]),
        round(mean(tps), 2),
        run["peak_mb"],
    )


def ladder(path: Path = FIXTURE) -> list[LadderRow]:
    data = json.loads(path.read_text())
    return [evaluate_run(data["golden"], r) for r in data["runs"]]


def drift_report(path: Path = FIXTURE) -> list[str]:
    """Compare consecutive recorded Nano runs; report base-model changes and score changes."""
    data = json.loads(path.read_text())
    golden = {g["id"]: g for g in data["golden"]}
    notes = []
    prev = None
    for rec in data["nano_drift"]:
        scores = {gid: score_output(golden[gid], out)[0] for gid, out in rec["outputs"].items()}
        if prev:
            if rec["recorded"] != prev[0]:
                notes.append(
                    f"base model changed {prev[0]} -> {rec['recorded']}: re-baseline required"
                )
            for gid, ok in scores.items():
                if prev[1].get(gid) and not ok:
                    notes.append(f"regression on {gid} after model change")
        prev = (rec["recorded"], scores)
    return notes


if __name__ == "__main__":
    print("SYNTHETIC FIXTURE: not device measurements")
    for row in ladder():
        print(row)
    print(drift_report())
