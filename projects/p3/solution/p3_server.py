"""P3 milestones 1-3: the `media-toolkit` MCP server (Python, mcp 2.3.0 `MCPServer`).

Tools (all paths relative to the media root; protocols, absolute paths and `..` refused):

| tool | kind | notes |
|---|---|---|
| probe, loudness | read-only | same contract as M9's servers and the Rust `rmcp` server |
| detect_scenes, detect_silence | read-only | ffmpeg `select`/`showinfo`, `silencedetect` |
| extract_frames | writes new files | at most 20 timestamps, inside the clip |
| transcode | expensive | preset allowlist only; asks first; progress notifications |
| cut | writes | an edit decision list (EDL), two-pass loudnorm; asks before overwriting |
| concat | writes | whole files, re-encoded; asks before overwriting |
| validate_pipeline | read-only | GStreamer parse + element allowlist (M14) |
| run_pipeline | runs GStreamer | validated first, `num-buffers` required, timeout |
| live_detect | runs GStreamer | needs 1.28's `onnxinference`; refuses cleanly without it |

Over Streamable HTTP the server is an OAuth *resource server*: a bearer token is required,
and tools that write need the `media:write` scope (checked per tool, not just at the door).
Over stdio or in-process it trusts the local user, like any CLI.

Run: `python p3_server.py <media-root>` (stdio) or `--http` (127.0.0.1:8766/mcp; needs a
token verifier, see `p3_auth.py`).
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Any, TypedDict

_HERE = Path(__file__).resolve().parent
for _p in (
    _HERE,
    _HERE.parents[1] / "common",
    *sorted((_HERE.parents[2] / "examples/python").glob("m*")),
):  # noqa: E501
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

import gst_validate as gv  # noqa: E402
import media_tools as mt  # noqa: E402
from mcp.server.auth.middleware.auth_context import get_access_token  # noqa: E402
from mcp.server.mcpserver import (  # noqa: E402
    AcceptedElicitation,
    Context,
    Elicit,
    ElicitationResult,
    MCPServer,
    Resolve,
)
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402
from mcp_types import ToolAnnotations  # noqa: E402
from media_probe_server import (  # noqa: E402
    FfmpegRunner,
    LoudnessResult,
    ProbeResult,
    Runner,
    parse_ffprobe,
    parse_loudnorm,
)
from pydantic import BaseModel  # noqa: E402

PRESETS: dict[str, list[str]] = {
    "h264_360p": ["-vf", "scale=-2:360", "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac"],
    "h264_720p": ["-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac"],
    "aac_audio": ["-vn", "-c:a", "aac", "-b:a", "128k"],
}
MAX_FRAMES = 20
MAX_EDL = 20
READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)
OVERWRITE = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=False)


class Confirm(BaseModel):
    confirm: bool


class Span(TypedDict):
    start: float
    end: float


class Scenes(TypedDict):
    path: str
    cuts: list[float]


class Silences(TypedDict):
    path: str
    silences: list[Span]


class Written(TypedDict):
    outputs: list[str]
    duration_s: float


class PipelineCheck(TypedDict):
    ok: bool
    problems: list[str]
    elements: list[str]


class PipelineRun(TypedDict):
    ok: bool
    timed_out: bool
    messages: list[str]
    level_peaks_db: list[float]


ROOT: dict[str, Path] = {}  # resolvers run at module level (see M9), so they find the root here


def safe(root: Path, rel: str) -> Path:
    try:
        return mt.resolve_in_root(root, rel)
    except mt.MediaToolError as e:
        raise ToolError(str(e)) from e


def require_scope(scope: str) -> None:
    """Over HTTP, a token is always present (the middleware rejects requests without one);
    tools that change files additionally need `scope`. No token = stdio/in-process."""
    tok = get_access_token()
    if tok is not None and scope not in tok.scopes:
        raise ToolError(f"token lacks scope {scope!r}")


def ask_transcode(path: str, preset: str) -> Elicit[Confirm] | Confirm:
    if preset not in PRESETS:
        return Confirm(confirm=False)  # don't ask a human about a request we'll refuse anyway
    return Elicit(
        f"Transcode {path} with preset {preset}? This re-encodes the whole file.", Confirm
    )


def ask_overwrite(out: str) -> Elicit[Confirm] | Confirm:
    root = ROOT.get("root")
    if root is not None and (root / out).exists():
        return Elicit(f"{out} exists. Overwrite it?", Confirm)
    return Confirm(confirm=True)  # nothing to overwrite: don't ask


def confirmed(answer: ElicitationResult[Confirm] | Confirm) -> bool:
    if isinstance(answer, Confirm):
        return answer.confirm
    return isinstance(answer, AcceptedElicitation) and answer.data.confirm


def validate_edl(edl: list[Span], duration: float) -> list[mt.Cut]:
    if not edl or len(edl) > MAX_EDL:
        raise ToolError(f"EDL needs 1-{MAX_EDL} entries")
    cuts, last_end = [], 0.0
    for i, e in enumerate(edl):
        s, t = float(e["start"]), float(e["end"])
        if not 0 <= s < t <= duration + 1e-6:
            raise ToolError(f"EDL entry {i} [{s}, {t}] is outside 0..{duration}")
        if s < last_end - 1e-6:
            raise ToolError(f"EDL entry {i} overlaps or goes backwards")
        cuts.append(mt.Cut(s, t))
        last_end = t
    return cuts


async def run_with_progress(argv: list[str], total_s: float, ctx: Context) -> None:
    """Run ffmpeg with `-progress pipe:1` and forward `out_time_us` as MCP progress."""
    proc = await asyncio.create_subprocess_exec(
        *argv[:1], "-progress", "pipe:1", "-nostats", *argv[1:],
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )  # fmt: skip
    assert proc.stdout is not None
    async for raw in proc.stdout:
        m = re.match(rb"out_time_us=(\d+)", raw)
        if m and total_s > 0:
            await ctx.report_progress(min(int(m.group(1)) / 1e6, total_s), total_s, "encoding")
    if await proc.wait() != 0:
        err = (await proc.stderr.read()).decode() if proc.stderr else ""
        raise ToolError(f"ffmpeg failed: {err.strip().splitlines()[-1:]}")
    await ctx.report_progress(total_s, total_s, "done")


def build_server(root: Path, runner: Runner | None = None, **mcp_kwargs: Any) -> MCPServer:
    root = Path(root).resolve()
    ROOT["root"] = root
    runner = runner or FfmpegRunner()
    srv = MCPServer(
        "media-toolkit",
        instructions="Media inspection and editing in a sandboxed media root. Read-only tools "
        "are free; transcode asks first; edits never overwrite without asking.",
        **mcp_kwargs,
    )

    @srv.tool(annotations=READ)
    def probe(path: str) -> ProbeResult:
        """Probe a media file with ffprobe: duration and streams. Read-only."""
        return parse_ffprobe(path, runner.ffprobe(safe(root, path)))

    @srv.tool(annotations=READ)
    def loudness(path: str) -> LoudnessResult:
        """Measure integrated loudness (LUFS) and true peak with ffmpeg loudnorm. Read-only."""
        return parse_loudnorm(path, runner.loudnorm(safe(root, path)))

    @srv.tool(annotations=READ)
    def detect_scenes(path: str, threshold: float = 0.3) -> Scenes:
        """Scene-cut timestamps (seconds) where ffmpeg's scene score exceeds threshold (0-1)."""
        if not 0 < threshold < 1:
            raise ToolError("threshold must be between 0 and 1")
        return {"path": path, "cuts": mt.scene_cuts(safe(root, path), threshold)}

    @srv.tool(annotations=READ)
    def detect_silence(path: str, noise_db: float = -40.0, min_s: float = 0.3) -> Silences:
        """Silent stretches (start/end seconds) below noise_db lasting at least min_s."""
        found = mt.silences(safe(root, path), noise_db, min_s)
        return {"path": path, "silences": [{"start": s, "end": e} for s, e in found]}

    @srv.tool(annotations=WRITE)
    def extract_frames(path: str, times: list[float], out_dir: str = "frames") -> Written:
        """Save one PNG per timestamp into out_dir (relative). At most 20 timestamps."""
        require_scope("media:write")
        src = safe(root, path)
        if not times or len(times) > MAX_FRAMES:
            raise ToolError(f"give 1-{MAX_FRAMES} timestamps")
        dur = mt.probe(src).duration
        if any(not 0 <= t < dur for t in times):
            raise ToolError(f"timestamps must be within 0..{dur}")
        out = safe(root, out_dir)
        out.mkdir(parents=True, exist_ok=True)
        names = []
        for t in times:
            f = out / f"{Path(path).stem}_{t:08.3f}.png"
            mt.thumbnail(src, f, t)
            names.append(str(f.relative_to(root)))
        return {"outputs": names, "duration_s": dur}

    @srv.tool(annotations=WRITE)
    async def transcode(
        path: str,
        preset: str,
        out: str,
        ctx: Context,
        answer: Annotated[ElicitationResult[Confirm] | Confirm, Resolve(ask_transcode)],
    ) -> Written:
        """Re-encode a file with a named preset (h264_360p, h264_720p, aac_audio). Asks first;
        reports progress. Free-form ffmpeg arguments are not accepted."""
        require_scope("media:write")
        if preset not in PRESETS:
            raise ToolError(f"unknown preset {preset!r}; allowed: {', '.join(PRESETS)}")
        src, dst = safe(root, path), safe(root, out)
        if dst.exists():
            raise ToolError(f"{out} exists; transcode never overwrites")
        if not confirmed(answer):
            return {"outputs": [], "duration_s": 0.0}
        dur = mt.probe(src).duration
        argv = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
                *PRESETS[preset], str(dst)]  # fmt: skip
        await run_with_progress(argv, dur, ctx)
        return {"outputs": [out], "duration_s": mt.probe(dst).duration}

    @srv.tool(annotations=OVERWRITE)
    async def cut(
        path: str,
        edl: list[Span],
        out: str,
        ctx: Context,
        answer: Annotated[ElicitationResult[Confirm] | Confirm, Resolve(ask_overwrite)],
        target_lufs: float = -16.0,
    ) -> Written:
        """Cut an edit decision list (start/end seconds, in order, no overlaps) from one
        source into out, loudness-normalised to target_lufs. Asks before overwriting."""
        require_scope("media:write")
        src, dst = safe(root, path), safe(root, out)
        if not -30 <= target_lufs <= -10:
            raise ToolError("target_lufs must be between -30 and -10")
        cuts = validate_edl(edl, mt.probe(src).duration)
        if not confirmed(answer):
            return {"outputs": [], "duration_s": 0.0}
        await ctx.report_progress(0, 2, "measuring loudness")
        await asyncio.to_thread(mt.render, src, cuts, dst, target_lufs)
        await ctx.report_progress(2, 2, "rendered")
        return {"outputs": [out], "duration_s": mt.probe(dst).duration}

    @srv.tool(annotations=OVERWRITE)
    async def concat(
        paths: list[str],
        out: str,
        answer: Annotated[ElicitationResult[Confirm] | Confirm, Resolve(ask_overwrite)],
    ) -> Written:
        """Join whole files (each with video and audio) end to end, re-encoded to H.264/AAC.
        Asks before overwriting."""
        require_scope("media:write")
        if not 2 <= len(paths) <= MAX_EDL:
            raise ToolError(f"give 2-{MAX_EDL} files")
        srcs, dst = [safe(root, p) for p in paths], safe(root, out)
        if not confirmed(answer):
            return {"outputs": [], "duration_s": 0.0}
        inputs = [a for s in srcs for a in ("-i", str(s))]
        pairs = "".join(f"[{i}:v][{i}:a]" for i in range(len(srcs)))
        argv = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs,
                "-filter_complex", f"{pairs}concat=n={len(srcs)}:v=1:a=1[v][a]",
                "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", str(dst)]  # fmt: skip
        await asyncio.to_thread(subprocess.run, argv, check=True, capture_output=True, timeout=300)
        return {"outputs": [out], "duration_s": mt.probe(dst).duration}

    @srv.tool(annotations=READ)
    def validate_pipeline(pipeline: str) -> PipelineCheck:
        """Parse a gst-launch pipeline and check it against the element allowlist,
        relative file locations and required num-buffers. Runs nothing."""
        try:
            p = gv.parse(pipeline)
        except gv.PipelineError as e:
            return {"ok": False, "problems": [str(e)], "elements": []}
        problems = gv.validate(p, root)
        return {"ok": not problems, "problems": problems,
                "elements": [e.factory for e in p.elements()]}  # fmt: skip

    @srv.tool(annotations=WRITE)
    def run_pipeline(pipeline: str, timeout_s: float = 10.0) -> PipelineRun:
        """Validate, then run a GStreamer pipeline in the media root with a timeout (max 30 s).
        Returns bus messages and any `level` peaks."""
        require_scope("media:write")
        if not gv.have_gst():
            raise ToolError("gst-launch-1.0 is not installed on this host")
        try:
            r = gv.run(pipeline, root, timeout=min(timeout_s, 30.0))
        except gv.PipelineError as e:
            raise ToolError(f"pipeline refused: {e}") from e
        return {"ok": r.ok, "timed_out": r.timed_out, "messages": r.messages[:50],
                "level_peaks_db": gv.level_peaks(r.messages)[:50]}  # fmt: skip

    @srv.tool(annotations=WRITE)
    async def live_detect(path: str, model: str, ctx: Context, frames: int = 100) -> PipelineRun:
        """Run an ONNX detector over a clip with GStreamer 1.28's onnxinference ->
        tensordecodebin and stream each detection message as a log notification.
        Refuses when the onnx plugin isn't installed."""
        require_scope("media:write")
        if (
            shutil.which("gst-inspect-1.0") is None
            or subprocess.run(["gst-inspect-1.0", "onnxinference"], capture_output=True).returncode
            != 0
        ):
            raise ToolError("onnxinference is not available on this host (GStreamer onnx plugin "
                            "not installed); needs GStreamer >= 1.28 with onnx")  # fmt: skip
        safe(root, path), safe(root, model)
        desc = (f"filesrc location={path} ! decodebin ! videoconvert ! videoscale ! "
                f"onnxinference model-file={model} ! tensordecodebin ! "
                f"identity num-buffers={frames} silent=false ! fakesink")  # fmt: skip
        r = await asyncio.to_thread(gv.run, desc, root, 30.0)
        for m in r.messages[:50]:
            await ctx.info(m, logger_name="live_detect")
        return {"ok": r.ok, "timed_out": r.timed_out, "messages": r.messages[:50],
                "level_peaks_db": []}  # fmt: skip

    @srv.resource("media://index", mime_type="application/json")
    def index() -> str:
        """Every media file under the root (relative paths)."""
        files = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
        return json.dumps(files)

    return srv


if __name__ == "__main__":
    server = build_server(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
    server.run()
