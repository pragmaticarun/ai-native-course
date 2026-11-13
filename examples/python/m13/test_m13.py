import os
from pathlib import Path

import availability as av
import decision_matrix as dm
import llama_quant as lq
import onnx_quant as oq
import privacy_router as pr
import pytest

HERE = Path(__file__).parent


# ------------------------------------------------------------ L13.1 decision matrix
def test_decision_matrix_and_vetoes():
    notes_app = dm.Requirements({"privacy": 3, "offline": 2, "latency": 1, "capability": 1})
    assert dm.decide(notes_app)[0] == "on_device"
    research = dm.Requirements({"capability": 3, "context_size": 2, "latency": 1})
    assert dm.decide(research)[0] in {"cloud", "hybrid"}
    best, totals = dm.decide(dm.Requirements({"capability": 3}, must_work_offline=True))
    assert "cloud" not in totals and best == "hybrid"
    with pytest.raises(ValueError):
        dm.decide(
            dm.Requirements({"privacy": 1}, data_must_stay_on_device=True, needs_large_context=True)
        )


# ------------------------------------------------------------ L13.2 availability
def test_a73_expected_answers_drive_the_ui():
    nano = av.Machine("genai-prompt")
    assert nano.on_status(av.A73_EXPECTED["genai-prompt (Gemini Nano)"]) is av.Ui.UNSUPPORTED
    assert nano.fallback == "cloud_or_litert_lm"
    speech = av.Machine("speech Basic")
    assert speech.on_status(av.A73_EXPECTED["speech-recognition Basic"]) is av.Ui.READY


def test_download_flow_and_errors():
    m = av.Machine("summarize")
    assert m.on_status(av.FeatureStatus.DOWNLOADABLE) is av.Ui.NEEDS_DOWNLOAD
    assert m.on_download_progress(0.5) is av.Ui.DOWNLOADING
    m.on_download_progress(0.3)
    assert m.progress == 0.5  # progress never goes backwards
    assert m.on_download_progress(1.0) is av.Ui.READY
    with pytest.raises(RuntimeError):
        av.Machine("x").on_run()
    m.on_run()
    assert m.on_error("BACKGROUND_USE_BLOCKED") is av.Ui.RETRY_IN_FOREGROUND
    m2 = av.Machine("y")
    assert [m2.on_error("BUSY") for _ in range(3)] == [
        av.Ui.BUSY_RETRY,
        av.Ui.BUSY_RETRY,
        av.Ui.QUOTA,
    ]
    assert av.Machine("z").on_error("PER_APP_BATTERY_USE_QUOTA_EXCEEDED") is av.Ui.QUOTA


# ------------------------------------------------------------ L13.4 router
def test_router_keeps_pii_local_or_refuses():
    dev = pr.DeviceState()
    assert pr.route(pr.Request("Call me on +91 98765 43210"), dev)[0] is pr.Route.LOCAL
    assert pr.route(pr.Request("mail priya@example.com", hard=True), dev)[0] is pr.Route.LOCAL
    no_local = pr.DeviceState(local_available=False)
    assert pr.route(pr.Request("card 4111 1111 1111 1111"), no_local)[0] is pr.Route.REFUSE
    assert (
        pr.route(pr.Request("my lab results", privacy=pr.Privacy.SENSITIVE, est_tokens=9000), dev)[
            0
        ]
        is pr.Route.REFUSE
    )


def test_router_non_private_paths():
    assert (
        pr.route(pr.Request("summarise this article", hard=True), pr.DeviceState())[0]
        is pr.Route.CLOUD
    )
    assert pr.route(pr.Request("tag this note"), pr.DeviceState())[0] is pr.Route.LOCAL
    assert pr.route(pr.Request("tag"), pr.DeviceState(online=False))[0] is pr.Route.LOCAL
    assert pr.route(pr.Request("tag", est_tokens=8000), pr.DeviceState())[0] is pr.Route.CLOUD
    assert pr.route(pr.Request("tag"), pr.DeviceState(battery_pct=10))[0] is pr.Route.CLOUD
    assert pr.detect_pii("nothing here") == []


def test_firebase_modes_on_an_a73_like_device():
    # Nano unavailable (A73): PREFER_ON_DEVICE quietly becomes cloud; ONLY_ON_DEVICE can't run.
    assert (
        pr.firebase_mode_route("PREFER_ON_DEVICE", nano_available=False, online=True)
        is pr.Route.CLOUD
    )
    assert (
        pr.firebase_mode_route("ONLY_ON_DEVICE", nano_available=False, online=True)
        is pr.Route.REFUSE
    )
    assert (
        pr.firebase_mode_route("PREFER_IN_CLOUD", nano_available=True, online=False)
        is pr.Route.LOCAL
    )
    assert (
        pr.firebase_mode_route("ONLY_IN_CLOUD", nano_available=True, online=False)
        is pr.Route.REFUSE
    )


# ------------------------------------------------------------ L13.6 quantization
def test_onnx_dynamic_int8_real(tmp_path):
    fp32, int8 = oq.run(tmp_path)
    assert int8.size_kb < fp32.size_kb / 3  # weights int8: ~4x smaller (plus graph overhead)
    assert fp32.accuracy > 0.95 and int8.agreement > 0.97


def test_parse_recorded_llama_perplexity_kld():
    k = lq.parse_kld((HERE / "fixtures" / "llama_kld_q4_0.txt").read_text())
    assert k["ppl_ratio"] > 1.0 and 0 < k["mean_kld"] < 1 and 50 < k["same_top_pct"] < 100


def test_kv_cache_formula():
    # stories15M: 6 layers, 6 KV heads x 48 dims; F16 cache at 128 tokens
    assert lq.kv_cache_bytes(6, 128, 6, 48, 2) == 884_736
    # weight quantization leaves it alone; halving KV heads (GQA) or context halves it
    assert lq.kv_cache_bytes(6, 128, 3, 48, 2) == lq.kv_cache_bytes(6, 64, 6, 48, 2) == 442_368


llama = pytest.mark.skipif(
    lq.tools() is None and not os.environ.get("M13_REQUIRE_LLAMA"),
    reason="set LLAMA_CPP_DIR + LLAMA_MODEL (CI llamacpp job does)",
)


@llama
def test_llama_cpp_quantize_real(tmp_path):
    t = lq.tools()
    assert t is not None, "M13_REQUIRE_LLAMA is set but llama.cpp/model not found"
    rows = {r.quant: r for r in lq.run(*t, tmp_path)}
    assert (
        rows["F32"].size_mb > rows["Q8_0"].size_mb > rows["Q4_K_M"].size_mb > rows["Q4_0"].size_mb
    )
    assert rows["Q8_0"].ppl_ratio < 1.01  # Q8_0 is nearly lossless here
    assert rows["Q8_0"].mean_kld < rows["Q4_K_M"].mean_kld < rows["Q4_0"].mean_kld
    assert rows["Q4_0"].same_top_pct < rows["Q8_0"].same_top_pct
    print("\n" + lq.table(list(rows.values())))
