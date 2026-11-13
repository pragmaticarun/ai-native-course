"""P7 evals: the media-analysis graph on ten generated recordings. Real ffmpeg for media,
mock ASR / summariser / judge, placeholder costs.

PROJECT_VARIANT=starter|solution pytest projects/p7/evals
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import media_tools as mt
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from p7_evals import Row, boundary_f1, compare, score_one, summary_passes
from p7_graph import build
from p7_kit import PROFILES, RECORDINGS, MockASR, make_recordings

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
logging.getLogger("langgraph").setLevel(logging.CRITICAL)


@pytest.fixture(scope="session")
def root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return make_recordings(tmp_path_factory.mktemp("p7") / "media")


@pytest.fixture(scope="session")
def rows(root: Path) -> list[Row]:
    return [score_one(root, r["id"], p) for p in PROFILES for r in RECORDINGS]


def test_recordings_match_their_spec(root: Path) -> None:
    for r in RECORDINGS:
        want = sum(s["seconds"] for s in r["shots"])
        assert abs(mt.probe(root / f"{r['id']}.mp4").duration - want) < 0.08, r["id"]


def test_boundary_f1_unit() -> None:
    assert boundary_f1([0, 2.0, 4.05], [0, 2.0, 4.0]) == 1.0
    assert boundary_f1([0, 2.0], [0, 2.0, 4.0]) == pytest.approx(2 / 3)
    assert boundary_f1([0, 3.0], [0, 2.0]) == 0.0


def test_chapters_found_on_every_recording(rows: list[Row]) -> None:
    misses = [(r.profile, r.rec_id, r.f1) for r in rows if r.f1 < 1.0]
    assert not misses, f"chapter boundaries missed (pauses need the audio track too): {misses}"


def test_judge_catches_the_invented_sponsor(rows: list[Row]) -> None:
    local = {r.rec_id: r.judged_ok for r in rows if r.profile == "local"}
    assert [k for k, ok in local.items() if not ok] == ["rec01", "rec05", "rec09"]
    assert all(r.judged_ok for r in rows if r.profile == "cloud")
    assert not summary_passes("A talk on bike maintenance basics. Sponsored by Acme.", "rec07")


def test_local_vs_cloud_table(rows: list[Row]) -> None:
    table = {t["profile"]: t for t in compare(rows)}
    assert table["local"]["wer"] > table["cloud"]["wer"] > 0
    assert table["local"]["judge_pass"] == "7/10" and table["cloud"]["judge_pass"] == "10/10"
    assert table["local"]["usd_per_media_hour (placeholder)"] == 0.0
    assert all(not r.problems and r.published for r in rows)


def test_concurrency_limit_holds(root: Path) -> None:
    for limit in (1, 2):
        row = score_one(root, "rec06", "cloud", max_concurrency=limit)
        assert 1 <= row.peak <= limit


def test_transient_asr_failure_is_retried(root: Path) -> None:
    asr = MockASR(PROFILES["cloud"], fail_first={"rec02@0.00"})
    g = build(asr)
    cfg = {"configurable": {"thread_id": "retry"}}
    g.invoke({"rec_id": "rec02", "path": str(root / "rec02.mp4"), "profile": "cloud"}, cfg)
    out = g.invoke(Command(resume="approve"), cfg)
    assert asr.calls.count("rec02@0.00") == 2
    assert out["chapters"][0]["start"] == 0.0 and out["published"]


def test_human_approval_pauses_and_resumes(root: Path) -> None:
    (root / "rec03.chapters.txt").unlink(missing_ok=True)
    saver = InMemorySaver()
    cfg = {"configurable": {"thread_id": "hitl"}}
    state = {"rec_id": "rec03", "path": str(root / "rec03.mp4"), "profile": "local"}
    build(MockASR(PROFILES["local"]), saver).invoke(state, cfg)
    g = build(MockASR(PROFILES["local"]), saver)  # a fresh process would rebuild the graph
    snap = g.get_state(cfg)
    assert snap.next == ("approve",)
    assert "summary" in snap.tasks[0].interrupts[0].value
    out = g.invoke(Command(resume="reject"), cfg)
    assert not out.get("published") and not (root / "rec03.chapters.txt").exists()


def test_highlight_reel_via_p3_server_passes_checks(root: Path) -> None:
    row = score_one(root, "rec04", "cloud", reel=True)
    assert row.problems == [] and row.published
    reel = root / "rec04_reel.mp4"
    assert abs(mt.probe(reel).duration - 2.4) <= 0.1
    assert abs(mt.loudness_lufs(reel) - -16.0) <= 1.0
