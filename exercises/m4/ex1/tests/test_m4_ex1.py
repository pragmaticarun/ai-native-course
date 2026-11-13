from _impl import load

impl = load(__file__)


def lossy(entries: list[str]) -> str:
    return f"{len(entries)} earlier messages about the media pipeline."


HISTORY = [
    "user: let's plan the transcoder",
    "user: settle the format\nDECISION: output is 48 kHz stereo AAC",
    "assistant: options are A, B, C",
    "CONSTRAINT: must run on a Galaxy A73 CPU",
    "FACT: input files are 4K HEVC",
    "user: what next?",
    "assistant: build the probe step",
]


def test_compacts_to_one_summary_plus_recent():
    out = impl.compact(HISTORY, 2, lossy)
    assert len(out) == 3
    assert out[0].startswith("SUMMARY: 5 earlier messages")
    assert out[1:] == HISTORY[-2:]


def test_pins_survive_verbatim():
    out = impl.compact(HISTORY, 2, lossy)
    for pin in (
        "DECISION: output is 48 kHz stereo AAC",
        "CONSTRAINT: must run on a Galaxy A73 CPU",
        "FACT: input files are 4K HEVC",
    ):
        assert pin in out[0]
    assert impl.fidelity(HISTORY, out) == 1.0


def test_fidelity_detects_loss():
    lost = ["SUMMARY: stuff", *HISTORY[-2:]]
    assert abs(impl.fidelity(HISTORY, lost) - 0.0) < 1e-9
    partial = ["SUMMARY: x\nFACT: input files are 4K HEVC", *HISTORY[-2:]]
    assert abs(impl.fidelity(HISTORY, partial) - 1 / 3) < 1e-9
    assert impl.fidelity(["no pins"], ["x"]) == 1.0


def test_short_history_unchanged():
    assert impl.compact(HISTORY[:2], 4, lossy) == HISTORY[:2]
