from pathlib import Path

import gst_validate as gv
from _impl import load

impl = load(__file__)


def test_pipeline_passes_the_validator(tmp_path: Path):
    desc = impl.pipeline("models/person.onnx", "clips/out.mkv")
    p = gv.parse(desc)
    assert gv.validate(p, tmp_path) == []
    names = [e.factory for e in p.elements()]
    assert names.index("onnxinference") < names.index("tensordecodebin")


def run(scores, fps=10):
    r = impl.Recorder()
    acts = [(i / fps, a) for i, s in enumerate(scores) if (a := r.on_frame(i / fps, s))]
    return r, acts


def test_needs_three_frames_to_start():
    _, acts = run([0.9, 0.9, 0.1, 0.9, 0.9, 0.9])
    assert acts == [(0.5, "start")]


def test_hysteresis_no_flapping():
    # hovers between off and on: stays recording, never stops
    r, acts = run([0.9] * 3 + [0.5, 0.45, 0.55] * 20)
    assert acts == [(0.2, "start")] and r.recording


def test_stops_after_two_quiet_seconds():
    r, acts = run([0.9] * 3 + [0.1] * 25)
    assert acts == [(0.2, "start"), (2.3, "stop")]
    assert r.segments == [(0.2, 2.3)]


def test_quiet_timer_resets_on_a_detection():
    _, acts = run([0.9] * 3 + [0.1] * 15 + [0.8] + [0.1] * 21)
    assert [a for _, a in acts] == ["start", "stop"] and acts[1][0] == 3.9
