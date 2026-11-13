"""P7 milestone 5: score the graph per profile and compare local vs cloud.

Real measurements: chapter boundary F1 against the generated ground truth, WER of the
(mock) transcripts, judge pass rate of summaries, wall-clock time of the graph on this
machine, peak concurrency. Simulated: cost per media hour and processing latency come
from the profiles' placeholder figures.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from media_eval import wer
from media_judge import judge_caption, mock_judge
from p7_graph import build, run
from p7_kit import BY_ID, PROFILES, MockASR, reference_chapters

TOLERANCE_S = 0.1


def boundary_f1(pred: list[float], ref: list[float], tol: float = TOLERANCE_S) -> float:
    """F1 of chapter starts (excluding 0, which every system gets free), each ref matched once."""
    p, r = [x for x in pred if x > 0], [x for x in ref if x > 0]
    if not p and not r:
        return 1.0
    used: set[int] = set()
    hits = 0
    for x in p:
        j = next((i for i, y in enumerate(r) if i not in used and abs(x - y) <= tol), None)
        if j is not None:
            used.add(j)
            hits += 1
    prec, rec = hits / len(p) if p else 0.0, hits / len(r) if r else 0.0
    return 0.0 if hits == 0 else 2 * prec * rec / (prec + rec)


def transcript_wer(chapters: list[dict[str, Any]], rec_id: str) -> float:
    ref = " ".join(c["transcript"] for c in reference_chapters(rec_id))
    hyp = " ".join(c["transcript"] for c in chapters)
    return wer(ref, hyp)


def summary_passes(summary: str, rec_id: str) -> bool:
    facts = (
        BY_ID[rec_id]["title"] + ". " + ". ".join(c["title"] for c in reference_chapters(rec_id))
    )
    return judge_caption(summary, facts, mock_judge).passed


@dataclass
class Row:
    rec_id: str
    profile: str
    f1: float
    wer: float
    judged_ok: bool
    media_s: float
    wall_s: float
    peak: int
    problems: list[str]
    published: bool


def score_one(
    root: Path,
    rec_id: str,
    profile: str,
    *,
    reel: bool = False,
    max_concurrency: int = 4,
    fail_first: set[str] | None = None,
    decision: str = "approve",
) -> Row:
    asr = MockASR(PROFILES[profile], fail_first=fail_first or set())
    g = build(asr)
    t = time.perf_counter()
    out = run(
        g,
        {
            "rec_id": rec_id,
            "path": str(root / f"{rec_id}.mp4"),
            "profile": profile,
            "want_reel": reel,
        },
        f"{profile}-{rec_id}",
        decision=decision,
        max_concurrency=max_concurrency,
    )
    wall = time.perf_counter() - t
    return Row(
        rec_id,
        profile,
        boundary_f1(
            [c["start"] for c in out["chapters"]], [c["start"] for c in reference_chapters(rec_id)]
        ),
        transcript_wer(out["chapters"], rec_id),
        summary_passes(out["summary"], rec_id),
        out["duration"],
        wall,
        asr.peak,
        out["problems"],
        bool(out.get("published")),
    )


def compare(rows: list[Row]) -> list[dict[str, Any]]:
    table = []
    for name, prof in PROFILES.items():
        rs = [r for r in rows if r.profile == name]
        if not rs:
            continue
        media_h = sum(r.media_s for r in rs) / 3600
        table.append(
            {
                "profile": name,
                "boundary_f1": round(sum(r.f1 for r in rs) / len(rs), 3),
                "wer": round(sum(r.wer for r in rs) / len(rs), 3),
                "judge_pass": f"{sum(r.judged_ok for r in rs)}/{len(rs)}",
                "usd_per_media_hour (placeholder)": prof.usd_per_media_hour,
                "simulated_s_per_media_min": round(prof.seconds_per_media_second * 60, 1),
                "measured_wall_s_per_media_min": round(
                    sum(r.wall_s for r in rs) / (media_h * 60), 1
                ),
            }
        )
    return table


def markdown(table: list[dict[str, Any]]) -> str:
    keys = list(table[0])
    lines = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    lines += ["| " + " | ".join(str(r[k]) for k in keys) + " |" for r in table]
    return "\n".join(lines)
