"""P3 evals: the media toolkit server, its guards, auth, the cross-language contract, and the
agent client's objective output checks. Real ffmpeg; no network; mock model.

PROJECT_VARIANT=starter|solution pytest projects/p3/evals
P3_REQUIRE_ALL=1 turns the TS/Rust/GStreamer skips into failures (the CI rust job sets it).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import httpx2
import mcp_types as t
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server.auth.provider import AccessToken
from p3_auth import StaticTokenVerifier, serve_http
from p3_client import EditorModel, ToolRouter, run_agent
from p3_contract import binary_stdio, python_stdio, run_all, ts_stdio
from p3_evals import check_output
from p3_fixtures import make_media_root
from p3_server import PRESETS, build_server

REPO = Path(__file__).resolve().parents[3]
VARIANT = os.environ.get("PROJECT_VARIANT", "solution")
HERE = REPO / "projects" / "p3" / VARIANT
RUST = Path(
    os.environ.get(
        "MEDIA_PROBE_RUST_BIN", REPO / "rust" / "media-probe" / "target" / "debug" / "media-probe"
    )
)
REQUIRE_ALL = os.environ.get("P3_REQUIRE_ALL") == "1"
HIGHLIGHT_EDL = [{"start": 4.0, "end": 5.56}, {"start": 8.48, "end": 10.08}]

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def need(ok: bool, reason: str) -> None:
    if not ok:
        if REQUIRE_ALL:
            pytest.fail(f"P3_REQUIRE_ALL=1 but {reason}")
        pytest.skip(reason)


@pytest.fixture(scope="module")
def media(tmp_path_factory) -> Path:
    return make_media_root(tmp_path_factory.mktemp("p3"))


def answer(confirm: bool, asked: list[str] | None = None):
    async def cb(ctx, params):
        if asked is not None:
            asked.append(params.message)
        return t.ElicitResult(action="accept", content={"confirm": confirm})

    return cb


def text(result) -> str:
    return "\n".join(getattr(c, "text", "") for c in result.content)


def ann(tool):
    assert tool.annotations is not None, tool.name
    return tool.annotations


async def call(media: Path, tool: str, args: dict, **client_kw):
    async with Client(build_server(media), **client_kw) as c:
        return await c.call_tool(tool, args)


# ------------------------------------------------------------------ M1 read-only tools
async def test_scene_and_silence_detection_match_the_fixture(media):
    scenes = await call(media, "detect_scenes", {"path": "match.mp4"})
    assert scenes.structured_content["cuts"] == pytest.approx([2.0, 3.52, 6.04, 8.04], abs=0.041)
    sil = (await call(media, "detect_silence", {"path": "match.mp4"})).structured_content
    assert [(round(s["start"], 2), round(s["end"], 2)) for s in sil["silences"]] == [(2.0, 3.52)]


async def test_tools_are_annotated_and_the_index_resource_lists_media(media):
    async with Client(build_server(media)) as c:
        tools = {tl.name: tl for tl in (await c.list_tools()).tools}
        assert ann(tools["probe"]).read_only_hint is True
        assert ann(tools["cut"]).destructive_hint is True
        assert ann(tools["transcode"]).read_only_hint is False
        res = await c.read_resource("media://index")
        assert "match.mp4" in getattr(res.contents[0], "text", "")


@pytest.mark.parametrize("bad", ["../etc/passwd", "/etc/passwd", "concat:a.mp4|b.mp4"])
async def test_paths_outside_the_media_root_are_refused(media, bad):
    assert (await call(media, "probe", {"path": bad})).is_error


# ------------------------------------------------------------------ M2 write tools, HITL, progress
async def test_transcode_asks_reports_progress_and_never_overwrites(media):
    asked: list[str] = []
    progress: list[float] = []

    async def on_progress(p, total, msg):
        progress.append(p)

    async with Client(build_server(media), elicitation_callback=answer(True, asked)) as c:
        args = {"path": "a.mp4", "preset": "h264_360p", "out": "a_360.mp4"}
        r = await c.call_tool("transcode", args, progress_callback=on_progress)
        assert not r.is_error and r.structured_content["outputs"] == ["a_360.mp4"]
        assert asked and "h264_360p" in asked[0]
        assert progress and progress == sorted(progress)
        again = await c.call_tool("transcode", args)
        assert again.is_error and "never overwrites" in text(again)


async def test_declined_transcode_writes_nothing(media):
    args = {"path": "a.mp4", "preset": "aac_audio", "out": "declined.m4a"}
    r = await call(media, "transcode", args, elicitation_callback=answer(False))
    assert r.structured_content["outputs"] == [] and not (media / "declined.m4a").exists()


async def test_only_allowlisted_presets_and_no_question_for_a_bad_one(media):
    asked: list[str] = []
    args = {"path": "a.mp4", "preset": "-vf scale=1:1", "out": "x.mp4"}
    r = await call(media, "transcode", args, elicitation_callback=answer(True, asked))
    assert r.is_error and not asked
    assert set(PRESETS) == {"h264_360p", "h264_720p", "aac_audio"}


@pytest.mark.parametrize(
    "edl",
    [
        [],
        [{"start": 2.0, "end": 1.0}],
        [{"start": 0.0, "end": 99.0}],
        [{"start": 0.0, "end": 2.0}, {"start": 1.0, "end": 3.0}],
    ],
)
async def test_bad_edls_are_refused(media, edl):
    assert (await call(media, "cut", {"path": "match.mp4", "edl": edl, "out": "bad.mp4"})).is_error


async def test_cut_asks_before_overwriting(media):
    asked: list[str] = []
    args = {"path": "match.mp4", "edl": HIGHLIGHT_EDL[:1], "out": "once.mp4"}
    async with Client(build_server(media), elicitation_callback=answer(False, asked)) as c:
        first = await c.call_tool("cut", args)
        assert first.structured_content["outputs"] == ["once.mp4"] and not asked
        second = await c.call_tool("cut", args)
        assert second.structured_content["outputs"] == [] and len(asked) == 1


async def test_extract_frames_caps_count_and_concat_joins(media):
    r = await call(media, "extract_frames", {"path": "match.mp4", "times": [0.5] * 21})
    assert r.is_error
    r = await call(media, "concat", {"paths": ["a.mp4", "b.mp4"], "out": "ab.mp4"})
    assert r.structured_content["duration_s"] == pytest.approx(3.2, abs=0.1)


# ------------------------------------------------------------------ M3 GStreamer tools
async def test_pipeline_validation_refuses_before_running(media):
    bad = "souphttpsrc location=http://example.com/x ! fakesink"
    r = (await call(media, "validate_pipeline", {"pipeline": bad})).structured_content
    assert r["ok"] is False and r["problems"]


async def test_run_pipeline_reports_level_peaks(media):
    need(shutil.which("gst-launch-1.0") is not None, "gst-launch-1.0 not installed")
    desc = "audiotestsrc num-buffers=20 volume=0.5 ! level post-messages=true ! fakesink"
    r = await call(media, "run_pipeline", {"pipeline": desc})
    assert not r.is_error and r.structured_content["ok"], r.content
    assert r.structured_content["level_peaks_db"]


async def test_live_detect_refuses_without_the_onnx_plugin(media):
    have = shutil.which("gst-inspect-1.0") is not None and (
        os.system("gst-inspect-1.0 onnxinference >/dev/null 2>&1") == 0
    )
    if have:
        pytest.skip("onnxinference is installed here; the refusal path can't be exercised")
    r = await call(media, "live_detect", {"path": "match.mp4", "model": "m.onnx"})
    assert r.is_error and "onnxinference" in text(r)


# ------------------------------------------------------------------ M4 HTTP + OAuth
def _tok(name: str, scopes: list[str], resource: str) -> AccessToken:
    return AccessToken(token=name, client_id="course", scopes=scopes, resource=resource)


async def test_http_oauth_401_metadata_scopes_and_audience(media):
    tokens: dict[str, AccessToken] = {}
    with serve_http(media, StaticTokenVerifier(tokens)) as url:
        tokens["r"] = _tok("r", ["media:read"], url)
        tokens["w"] = _tok("w", ["media:read", "media:write"], url)
        tokens["elsewhere"] = _tok("elsewhere", ["media:read", "media:write"], "http://other/mcp")
        ping = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        async with httpx2.AsyncClient() as h:
            r = await h.post(url, json=ping)
            assert r.status_code == 401
            assert "resource_metadata=" in r.headers["www-authenticate"]
            meta_url = r.headers["www-authenticate"].split('resource_metadata="')[1].split('"')[0]
            meta = (await h.get(meta_url)).json()
            assert meta["resource"].rstrip("/") == url and "media:read" in meta["scopes_supported"]
            r = await h.post(url, json=ping, headers={"Authorization": "Bearer elsewhere"})
            assert r.status_code == 401

        async def frames(token: str):
            headers = {"Authorization": f"Bearer {token}"}
            async with httpx2.AsyncClient(headers=headers) as h:
                async with Client(streamable_http_client(url, http_client=h)) as c:
                    return await c.call_tool(
                        "extract_frames", {"path": "match.mp4", "times": [1.0]}
                    )

        assert "media:write" in text(await frames("r"))
        assert not (await frames("w")).is_error


# ------------------------------------------------------------------ M5 contract across languages
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_contract_in_process(media, mode):
    report, extended = await run_all(build_server(media), mode=mode)
    assert report.violations == [] and extended == []
    assert report.protocol_version == ("2026-07-28" if mode == "auto" else "2025-11-25")


async def test_contract_python_stdio(media):
    report, extended = await run_all(python_stdio(HERE / "p3_server.py", media))
    assert report.violations == [] and extended == []


async def test_contract_typescript_stdio(media):
    need((REPO / "node_modules" / "@modelcontextprotocol").exists(), "run pnpm install first")
    entry = HERE / "ts" / "mediaToolkitStdio.ts"
    for mode in ("auto", "legacy"):
        report, extended = await run_all(ts_stdio(entry, media), mode=mode)
        assert report.violations == [] and extended == [], mode
        assert {"probe", "loudness", "transcode"} <= set(report.tools)


@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_contract_rust_rmcp(media, mode):
    need(RUST.exists(), f"Rust server not built at {RUST} (cargo build in rust/media-probe)")
    report, extended = await run_all(binary_stdio(RUST, media), mode=mode)
    assert report.violations == [] and extended == []
    assert report.tools == ["loudness", "probe"]


# ------------------------------------------------------------------ M6 agent client + evals
async def test_agent_edits_a_highlight_that_passes_objective_checks(media):
    async with ToolRouter() as router:
        await router.add("python", build_server(media))
        if RUST.exists():
            await router.add("rust", binary_stdio(RUST, media))
        else:
            need(False, "Rust server not built; routing to rust can't be checked")
        run = await run_agent(router, EditorModel(), "2-shot highlight of match.mp4 at -16 LUFS")
        assert run.calls == ["probe", "detect_scenes", "detect_silence", "cut", "loudness"]
        assert dict(router.log)["probe"] == "rust" and dict(router.log)["loudness"] == "rust"
        assert dict(router.log)["cut"] == "python"
    check = check_output(media / "highlight.mp4", HIGHLIGHT_EDL, -16.0)
    assert check.ok, check.problems
    assert check.duration_s == pytest.approx(3.2, abs=0.1)


def test_objective_checks_catch_a_wrong_edit(media):
    check = check_output(media / "a.mp4", HIGHLIGHT_EDL, -16.0)
    assert not check.ok and any("duration" in p for p in check.problems)
