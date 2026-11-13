import pytest
from _impl import load

impl = load(__file__)

# What the docs imply a Galaxy A73 answers (NOT captured from the device).
A73 = {"genai-prompt": "UNAVAILABLE", "speech-recognition-basic": "AVAILABLE"}


def test_a73_nano_is_unsupported_with_a_fallback():
    m = impl.Machine()
    assert m.on_status(A73["genai-prompt"]) == "unsupported"
    assert m.fallback == "litert_lm_cpu"


def test_a73_speech_basic_is_ready():
    assert impl.Machine().on_status(A73["speech-recognition-basic"]) == "ready"


def test_download_flow_never_goes_backwards():
    m = impl.Machine()
    assert m.on_status("DOWNLOADABLE") == "needs_download"
    assert m.on_status("DOWNLOADING") == "downloading"
    assert m.on_progress(0.7) == "downloading"
    m.on_progress(0.4)
    assert m.progress == 0.7
    assert m.on_progress(1.0) == "ready"


def test_runtime_errors():
    assert impl.Machine().on_error("BACKGROUND_USE_BLOCKED") == "foreground_needed"
    m = impl.Machine()
    assert [m.on_error("BUSY") for _ in range(3)] == ["retrying", "retrying", "fallback"]
    q = impl.Machine()
    assert q.on_error("PER_APP_BATTERY_USE_QUOTA_EXCEEDED") == "fallback" and q.fallback


def test_unknowns_raise():
    with pytest.raises(ValueError):
        impl.Machine().on_status("MAYBE")
    with pytest.raises(ValueError):
        impl.Machine().on_error("SOMETHING_ELSE")
