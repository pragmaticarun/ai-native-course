import pytest
import sampling
from structured_output import Event, demo_model, extract_event
from token_accounting import Prices, run_cost
from unit_converter_pydantic_ai import make_agent
from unit_converter_raw import ScriptedModel, ToolCall, ask, convert, run_tool, scripted_brain

from aincourse import AssistantTurn


def test_softmax_and_greedy():
    probs = sampling.softmax(sampling.TOY_LOGITS, 1.0)
    assert abs(sum(probs.values()) - 1) < 1e-9
    assert sampling.softmax(sampling.TOY_LOGITS, 0)["cat"] == 1.0
    hot, cold = (
        sampling.softmax(sampling.TOY_LOGITS, 2.0),
        sampling.softmax(sampling.TOY_LOGITS, 0.5),
    )
    assert hot["C++"] > cold["C++"]


def test_top_p_and_seeded_sampling():
    kept = sampling.top_p_filter(sampling.softmax(sampling.TOY_LOGITS), 0.5)
    assert list(kept) == ["cat"]
    assert sampling.sample(sampling.TOY_LOGITS, 1.0, 1.0, 7) == sampling.sample(
        sampling.TOY_LOGITS, 1.0, 1.0, 7
    )
    assert sampling.approx_tokens("x" * 40) == 10


def test_structured_output_repairs_once():
    model = demo_model()
    assert extract_event(model, "...") == Event(
        title="Rust meetup", date="2026-11-20", location="Bengaluru"
    )
    assert len(model.calls) == 2
    assert "invalid" in model.calls[1][-1].content


def test_structured_output_gives_up():
    bad = ScriptedModel([AssistantTurn(text="not json")] * 3)
    with pytest.raises(ValueError, match="3 attempts"):
        extract_event(bad, "...")


def test_raw_tool_loop():
    model = ScriptedModel(scripted_brain)
    assert ask(model, "marathon?") == "That is 26.2187 miles."
    assert [m.role for m in model.calls[-1]] == ["system", "user", "assistant", "tool"]


def test_tool_errors_become_text():
    assert run_tool(ToolCall("convert", {"value": 1, "from_unit": "C", "to_unit": "F"})).startswith(
        "error: unsupported"
    )
    assert run_tool(ToolCall("nope", {})).startswith("error: unknown tool")
    assert convert(10, "kg", "lb") == 22.0462


def test_pydantic_ai_converter():
    assert make_agent().run_sync("marathon?").output == "That is 26.2187 miles."


def test_caching_is_cheaper():
    p = Prices(1.0, 0.1, 4.0)
    no_cache = run_cost(6000, 300, 200, 20, p, cache=False)
    cached = run_cost(6000, 300, 200, 20, p, cache=True)
    assert cached < no_cache
    assert run_cost(6000, 300, 200, 1, p, True) == run_cost(6000, 300, 200, 1, p, False)


def test_image_budget_math():
    from image_budget import ffmpeg_frame_cmd, fit_long_edge, image_part, to_original

    w, h, s = fit_long_edge(3840, 2160, 1280)
    assert (w, h) == (1280, 720) and to_original(640, 360, s) == (1920, 1080)
    assert fit_long_edge(800, 600, 1280) == (800, 600, 1.0)  # never upscale
    assert ffmpeg_frame_cmd("in.mp4", 12.5, "f.png")[4:8] == ["-ss", "12.500", "-i", "in.mp4"]
    assert image_part(b"\x89PNG")["data"] == "iVBORw=="


@pytest.mark.skipif(__import__("shutil").which("ffmpeg") is None, reason="ffmpeg not installed")
def test_grab_frame_with_real_ffmpeg(tmp_path):
    import subprocess

    from image_budget import grab_frame

    video = tmp_path / "test.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=320x240:rate=10",
            str(video),
        ],
        check=True,
    )
    png = grab_frame(str(video), 1.0, str(tmp_path / "frame.png"))
    assert png.read_bytes()[:4] == b"\x89PNG"
