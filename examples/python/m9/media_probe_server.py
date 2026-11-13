"""M9 worked example: the "media-probe" MCP server (mcp 2.3.0, `MCPServer`).

Tools
* `probe(path)`: ffprobe summary (duration, streams), read-only, structured output;
* `loudness(path)`: integrated loudness (LUFS) and true peak via ffmpeg `loudnorm`;
* `delete_clip(path)`: destructive, so it asks the user first. On the 2026-07-28 protocol
  the question rides an `input_required` result (multi round-trip request); on older
  protocol versions the SDK sends a classic `elicitation/create` request instead.
Resource `media://index` lists the files; prompt `chapterise` is a reusable instruction.

Same contract as the Rust (`rust/media-probe`) and Kotlin servers: `contract.py` checks
all of them. Paths are resolved inside a media root; `..` and absolute paths are refused.

Run: `uv run python media_probe_server.py <media-root>` (stdio) or add `--http` for
Streamable HTTP on 127.0.0.1:8765/mcp.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Protocol, TypedDict

from mcp.server.caching import CacheHint
from mcp.server.mcpserver import AcceptedElicitation, Elicit, ElicitationResult, MCPServer, Resolve
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel


class Stream(TypedDict, total=False):
    codec_type: str
    codec_name: str
    width: int
    height: int
    sample_rate: int


class ProbeResult(TypedDict):
    path: str
    duration_s: float
    streams: list[Stream]


class LoudnessResult(TypedDict):
    path: str
    integrated_lufs: float
    true_peak_dbtp: float


class Runner(Protocol):
    def ffprobe(self, file: Path) -> str: ...
    def loudnorm(self, file: Path) -> str: ...


class FfmpegRunner:
    def ffprobe(self, file: Path) -> str:
        cmd = ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(file)]
        return subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60).stdout

    def loudnorm(self, file: Path) -> str:
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(file),
               "-af", "loudnorm=print_format=json", "-f", "null", "-"]  # fmt: skip
        return subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600).stderr


class FixtureRunner:
    """Offline runner for tests: canned ffprobe/loudnorm output."""

    def __init__(self, ffprobe_json: str, lufs: float = -16.2, peak: float = -1.4) -> None:
        self.ffprobe_json, self.lufs, self.peak = ffprobe_json, lufs, peak
        self.calls: list[str] = []

    def ffprobe(self, file: Path) -> str:
        self.calls.append(f"ffprobe {file.name}")
        return self.ffprobe_json

    def loudnorm(self, file: Path) -> str:
        self.calls.append(f"loudnorm {file.name}")
        return f'[Parsed_loudnorm_0]\n{{"input_i" : "{self.lufs}", "input_tp" : "{self.peak}"}}\n'


def parse_ffprobe(path: str, text: str) -> ProbeResult:
    data = json.loads(text)
    streams: list[Stream] = []
    for s in data.get("streams", []):
        st: Stream = {
            "codec_type": s.get("codec_type", "unknown"),
            "codec_name": s.get("codec_name", "unknown"),
        }
        for key in ("width", "height", "sample_rate"):
            if key in s:
                st[key] = int(s[key])  # type: ignore[literal-required]
        streams.append(st)
    return {"path": path, "duration_s": float(data["format"]["duration"]), "streams": streams}


def parse_loudnorm(path: str, stderr: str) -> LoudnessResult:
    block = json.loads(stderr[stderr.rindex("{") : stderr.rindex("}") + 1])
    return {
        "path": path,
        "integrated_lufs": float(block["input_i"]),
        "true_peak_dbtp": float(block["input_tp"]),
    }


def resolve_in_root(root: Path, rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts:
        # ToolError = an expected failure: the message reaches the model as an is_error
        # result. Any other exception is logged as a crash and the message is hidden.
        raise ToolError(f"path escapes media root: {rel}")
    return root / p


class ConfirmDelete(BaseModel):
    confirm: bool


def ask_first(path: str) -> Elicit[ConfirmDelete]:
    """Resolver for delete_clip's `answer` parameter. Module level on purpose: with
    `from __future__ import annotations` the SDK evaluates the tool's annotations
    against module globals, so a resolver defined inside build_server is not found."""
    return Elicit(f"Permanently delete {path}?", ConfirmDelete)


def build_server(
    root: Path, runner: Runner, on_delete: Callable[[Path], None] | None = None
) -> MCPServer:
    root = Path(root)
    srv = MCPServer(
        "media-probe",
        instructions="Read-only media inspection; delete_clip always asks the user first.",
        cache_hints={"tools/list": CacheHint(ttl_ms=60_000, scope="public")},
    )
    deleter = on_delete or (lambda f: f.unlink())

    @srv.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
    def probe(path: str) -> ProbeResult:
        """Probe a media file with ffprobe: duration and streams. Read-only."""
        return parse_ffprobe(path, runner.ffprobe(resolve_in_root(root, path)))

    @srv.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
    def loudness(path: str) -> LoudnessResult:
        """Measure integrated loudness (LUFS) and true peak with ffmpeg loudnorm. Read-only."""
        return parse_loudnorm(path, runner.loudnorm(resolve_in_root(root, path)))

    @srv.tool(annotations=ToolAnnotations(destructive_hint=True, idempotent_hint=True))
    def delete_clip(
        path: str, answer: Annotated[ElicitationResult[ConfirmDelete], Resolve(ask_first)]
    ) -> str:
        """Delete a clip from the media root. Asks the user to confirm every time."""
        file = resolve_in_root(root, path)
        if isinstance(answer, AcceptedElicitation) and answer.data.confirm:
            deleter(file)
            return f"deleted {path}"
        return f"kept {path}"

    @srv.resource("media://index", mime_type="application/json")
    def index() -> str:
        """Every media file under the root (relative paths)."""
        files = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
        return json.dumps(files)

    @srv.prompt()
    def chapterise(path: str) -> str:
        """Ask the model to propose chapters for a recording."""
        return f"Call probe on {path}, then propose chapters (mm:ss title), one per scene change."

    return srv


def tool_result_json(result: Any) -> dict[str, Any]:
    """Structured content if present, else parse the first text block."""
    return result.structured_content or json.loads(result.content[0].text)


if __name__ == "__main__":
    server = build_server(Path(sys.argv[1] if len(sys.argv) > 1 else "."), FfmpegRunner())
    if "--http" in sys.argv:
        server.run(transport="streamable-http", port=8765)
    else:
        server.run()
