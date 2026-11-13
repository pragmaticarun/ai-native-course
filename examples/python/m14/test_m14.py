import json
from pathlib import Path

import gst_validate as gv
import highlight_reel as hr
import media_judge as mj
import media_tools as mt
import pytest
import speech_pipeline as sp
import vision_cascade as vc

ffmpeg = pytest.mark.skipif(not mt.have_ffmpeg(), reason="ffmpeg/ffprobe not installed")
gst = pytest.mark.skipif(not gv.have_gst(), reason="gst-launch-1.0 not installed")


@pytest.fixture(scope="module")
def match_clip(tmp_path_factory) -> Path:
    shots, _, _ = hr.load_fixture()
    return mt.make_clip(tmp_path_factory.mktemp("m14") / "match.mp4", shots)


# ------------------------------------------------------------ media_tools
def test_resolve_in_root_blocks_protocols_and_escapes(tmp_path):
    assert mt.resolve_in_root(tmp_path, "a/b.mp4") == (tmp_path / "a/b.mp4").resolve()
    for bad in ["concat:a.mp4|b.mp4", "http://x/y.mp4", "pipe:0", "../etc/passwd", "/etc/passwd"]:
        with pytest.raises(mt.MediaToolError):
            mt.resolve_in_root(tmp_path, bad)


def test_parse_ffprobe_from_recorded_json():
    text = json.dumps({
        "format": {"duration": "4.000000"},
        "streams": [
            {"codec_type": "video", "width": 640, "height": 360, "avg_frame_rate": "30000/1001"},
            {"codec_type": "audio", "sample_rate": "44100"},
        ],
    })  # fmt: skip
    p = mt.parse_ffprobe(text)
    assert (p.width, p.height, p.audio_streams, p.sample_rate) == (640, 360, 1, 44100)
    assert p.fps == pytest.approx(29.97, abs=0.01)


def test_concat_argv_is_a_list_and_rejects_bad_cuts(tmp_path):
    argv = mt.concat_argv(
        tmp_path / "in.mp4", [mt.Cut(0, 1), mt.Cut(2, 3)], tmp_path / "o.mp4", None
    )
    assert argv[0] == "ffmpeg" and "concat=n=2:v=1:a=1" in argv[argv.index("-filter_complex") + 1]
    with pytest.raises(mt.MediaToolError):
        mt.concat_argv(tmp_path / "in.mp4", [mt.Cut(2, 1)], tmp_path / "o.mp4", None)
    with pytest.raises(mt.MediaToolError):
        mt.concat_argv(tmp_path / "in.mp4", [], tmp_path / "o.mp4", None)


@ffmpeg
def test_probe_scenes_silence_loudness(match_clip):
    p = mt.probe(match_clip)
    assert p.duration == pytest.approx(10.52, abs=0.05)
    assert (p.width, p.height, p.fps, p.video_streams, p.audio_streams) == (320, 240, 25.0, 1, 1)
    assert mt.scene_cuts(match_clip) == pytest.approx([2.0, 3.52, 6.04, 8.04], abs=0.041)
    (s, e), *_ = mt.silences(match_clip)
    assert (s, e) == pytest.approx((2.0, 3.52), abs=0.05)
    assert -30 < mt.loudness_lufs(match_clip) < -15


@ffmpeg
def test_near_equal_luma_cut_is_missed(tmp_path):
    """Observed with ffmpeg 7.1 (box) and in CI: pure red -> green, whose luma is nearly equal,
    is not detected as a cut. Choose fixture colours (and trust detectors) accordingly."""
    clip = mt.make_clip(tmp_path / "rg.mp4", [mt.Shot("red", 1.0, 440), mt.Shot("green", 1.0, 440)])
    assert mt.scene_cuts(clip) == []


@ffmpeg
def test_thumbnails(match_clip, tmp_path):
    assert mt.thumbnail(match_clip, tmp_path / "t.png", 4.0).stat().st_size > 0
    assert mt.best_thumbnail(match_clip, tmp_path / "b.png").stat().st_size > 0


# ------------------------------------------------------------ highlight reel WE
def test_plan_edl_respects_budget_order_and_margin():
    shots = [mt.Cut(0, 2), mt.Cut(2, 3.52), mt.Cut(3.52, 6.04), mt.Cut(6.04, 8.04)]
    plan = hr.plan_edl(shots, [0.4, 0.0, 1.0, 0.9], budget_s=3.3)
    assert [e.shot for e in plan.entries] == [2, 3]  # best two fit; back in time order
    assert plan.seconds <= 3.3
    assert all(e.src_in >= shots[e.shot].start + 0.2 for e in plan.entries)
    assert plan.record_points() == [pytest.approx(1.6)]
    assert hr.plan_edl(shots, [0.1] * 4, budget_s=10).entries == []  # nothing worth keeping


@ffmpeg
def test_highlight_reel_end_to_end(match_clip, tmp_path):
    _, segments, captions = hr.load_fixture()
    rep = hr.run(match_clip, tmp_path / "reel.mp4", hr.FixedTranscriber(segments),
                 hr.KeywordScorer(), captions)  # fmt: skip
    assert rep.failures == [], rep.trace
    assert [e.shot for e in rep.plan.entries] == [2, 4]
    assert mt.loudness_lufs(rep.out) == pytest.approx(-16.0, abs=1.0)


@ffmpeg
def test_verify_catches_a_wrong_render(match_clip, tmp_path):
    plan = hr.Plan([hr.EdlEntry(2, 3.72, 5.32, 1, ""), hr.EdlEntry(4, 8.24, 9.84, 1, "")], -16.0)
    out = mt.render(match_clip, [mt.Cut(3.72, 5.32)], tmp_path / "short.mp4", -23.0)  # one cut only
    fails = hr.verify(out, plan)
    assert any("duration" in f for f in fails) and any("loudness" in f for f in fails)


# ------------------------------------------------------------ gstreamer
def test_gst_parse_tee_and_caps():
    p = gv.parse("videotestsrc num-buffers=10 ! video/x-raw,width=320 ! tee name=t "
                 "t. ! queue ! fakesink t. ! queue ! videoconvert ! fakesink")  # fmt: skip
    assert [e.factory for e in p.elements()][:3] == ["videotestsrc", "tee", "queue"]
    assert len(p.branches) == 3 and p.elements()[0].props == {"num-buffers": "10"}


def test_gst_validator_rejects_unsafe(tmp_path):
    bad = [
        ("souphttpsrc location=http://x ! fakesink", "not allowed"),
        ("filesrc location=/etc/passwd ! fakesink", "relative"),
        ("filesrc location=../../x ! fakesink", "escapes"),
        ("videotestsrc ! fakesink", "num-buffers"),
        ("playbin uri=file:///x", "not allowed"),
    ]
    for desc, why in bad:
        assert any(why in pr for pr in gv.validate(gv.parse(desc), tmp_path)), desc
    assert gv.validate(gv.parse("audiotestsrc num-buffers=5 ! level ! fakesink"), tmp_path) == []
    with pytest.raises(gv.PipelineError):
        gv.parse("videotestsrc ; rm -rf /")


def test_gst_ml_elements_are_allowlisted_but_untested():
    p = gv.parse("filesrc location=in.mp4 ! decodebin ! videoconvert ! onnxinference "
                 "model-file=det.onnx ! tensordecodebin ! fakesink")  # fmt: skip
    assert gv.validate(p, Path("/tmp")) == []


@gst
def test_gst_run_level_messages(tmp_path):
    res = gv.run("audiotestsrc num-buffers=20 volume=0.5 ! audioconvert ! level post-messages=true "
                 "! fakesink", tmp_path)  # fmt: skip
    assert res.ok and not res.timed_out
    peaks = gv.level_peaks(res.messages)
    assert peaks and all(-10 < p < 0 for p in peaks)


@gst
def test_gst_run_writes_inside_sandbox(tmp_path):
    res = gv.run("videotestsrc num-buffers=1 ! videoconvert ! pngenc ! filesink location=f.png",
                 tmp_path)  # fmt: skip
    assert res.ok and (tmp_path / "f.png").stat().st_size > 0


@gst
def test_gst_timeout(tmp_path):
    allowed = gv.ALLOWED
    res = gv.run("audiotestsrc num-buffers=100000000 is-live=true ! fakesink sync=true", tmp_path,
                 timeout=1.0)  # fmt: skip
    assert res.timed_out and allowed is gv.ALLOWED


# ------------------------------------------------------------ speech
@ffmpeg
def test_speech_pipeline_vad_and_toy_diarization(tmp_path):
    shots = [mt.Shot("black", s, hz) for s, hz in
             [(0.6, None), (1.2, 300), (0.6, None), (1.0, 600), (0.4, None), (0.8, 300), (0.4, None)]]  # fmt: skip  # noqa: E501
    clip = mt.make_clip(tmp_path / "talk.mp4", shots)
    utts = sp.transcribe(clip, sp.scripted_asr(["hello there", "hi how are you", "fine thanks"]))
    assert [u.speaker for u in utts] == ["SPEAKER_00", "SPEAKER_01", "SPEAKER_00"]
    assert utts[0].start == pytest.approx(0.6, abs=0.1) and utts[0].end == pytest.approx(
        1.8, abs=0.1
    )
    fixed = sp.post_process(utts, lambda t: t.capitalize() + ".")
    assert fixed[1].text == "Hi how are you."


def test_latency_budgets_and_corpus_wer():
    assert sp.batch_latency(60, 0.5) == 90
    assert sp.streaming_first_text(1.0, 0.5, 0.1) == pytest.approx(1.6)
    assert sp.streaming_keeps_up(0.8) and not sp.streaming_keeps_up(1.2)
    # word-weighted: 1 error in 1 word + 0 errors in 9 words = 0.1, not mean(1.0, 0.0) = 0.5
    assert sp.corpus_wer(
        ["yes", "a b c d e f g h i"], ["no", "a b c d e f g h i"]
    ) == pytest.approx(0.1)


# ------------------------------------------------------------ vision
def test_sampling_and_cost():
    assert vc.uniform_times(3.0, 1.0) == [0.0, 1.0, 2.0]
    assert vc.scene_times([2.0, 3.52], 5.0) == [0.2, 2.2, 3.72]
    assert vc.budgeted(list(range(10)), 3) == [0, 3, 6]
    c = vc.cost(frames=10, tokens_per_frame=250, usd_per_mtok=2.0, s_per_call=0.5)
    assert (c.tokens, c.dollars, c.seconds) == (2500, 0.005, 5.0)


@ffmpeg
def test_cascade_skips_black_frames(match_clip):
    calls: list[float] = []

    def vlm(t: float) -> str:
        calls.append(t)
        return "x"

    res = vc.cascade(match_clip, mt.probe(match_clip).duration, vlm)
    assert (res.candidates, res.sent_to_vlm) == (5, 4)  # the black shot never reaches the VLM
    assert len(calls) == 4 and len(vc.uniform_times(10.52, 0.5)) == 22


# ------------------------------------------------------------ judge & privacy
def test_judge_rubric_with_mock():
    facts = "striker scores a goal from distance"
    assert not mj.judge_caption("Messi scores a goal", facts, mj.mock_judge).passed
    assert mj.judge_caption("Striker celebrates a goal", facts, mj.mock_judge).passed
    assert "unparseable" in mj.judge_caption("x", facts, lambda p: "not json").reason


def test_privacy_findings():
    m = {"faces_detected": 2, "voices": True, "source": "screen_recording",
         "ocr_text": ["Password: hunter2"], "upload_to_cloud": True, "privacy_class": "on_device_only"}  # fmt: skip  # noqa: E501
    assert len(mj.privacy_findings(m)) == 4
    assert mj.privacy_findings({"faces_detected": 1, "faces_blurred": True}) == []
