"""P3 kit (provided): the contract every media-toolkit server must keep.

* `core`: M9's probe/loudness contract (`examples/python/m9/contract.py`), unchanged, so the
  Python, TypeScript and Rust servers are held to exactly the same promises;
* `extended`: P3's extra promises for whichever toolkit tools a server offers: annotations
  match what the tool does, every path argument refuses escapes, transcode only takes
  allowlisted presets, and EDLs are validated before anything runs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_EX = Path(__file__).resolve().parents[3] / "examples" / "python"
if str(_EX / "m9") not in sys.path:
    sys.path.append(str(_EX / "m9"))

from contract import Expect, Report, check_contract  # noqa: E402,F401
from mcp import Client, StdioServerParameters  # noqa: E402
from mcp.shared.exceptions import MCPError  # noqa: E402

READ_ONLY = {"probe", "loudness", "detect_scenes", "detect_silence", "validate_pipeline"}
WRITES = {"extract_frames", "transcode", "cut", "concat", "run_pipeline", "live_detect"}
TONE = Expect("tone.wav", 2.0, stream_types=("audio",))
ESCAPES = ("../secret.mp4", "/etc/passwd", "concat:a.mp4|b.mp4")


async def refused(client: Client, name: str, args: dict[str, Any]) -> bool:
    """An is_error result or a protocol error both count as a refusal."""
    try:
        return bool((await client.call_tool(name, args)).is_error)
    except MCPError:
        return True


async def check_extended(client: Client) -> list[str]:
    v: list[str] = []
    tools = {t.name: t for t in (await client.list_tools()).tools}
    for name, t in tools.items():
        ro = t.annotations.read_only_hint if t.annotations else None
        if name in READ_ONLY and ro is not True:
            v.append(f"{name}: should be annotated read-only")
        if name in WRITES and ro is not False:
            v.append(f"{name}: writes files but is not annotated read_only_hint=false")
    for name in sorted(set(tools) & {"probe", "loudness", "detect_scenes", "detect_silence"}):
        for bad in ESCAPES:
            if not await refused(client, name, {"path": bad}):
                v.append(f"{name}: path escape not refused: {bad}")
    if "transcode" in tools:
        args = {"path": "tone.wav", "preset": "-f lavfi -i x", "out": "x.mp4"}
        if not await refused(client, "transcode", args):
            v.append("transcode accepted a non-allowlisted preset")
    if "cut" in tools:
        for edl in ([], [{"start": 1.0, "end": 0.5}], [{"start": 0, "end": 99}]):
            if not await refused(client, "cut", {"path": "tone.wav", "edl": edl, "out": "o.mp4"}):
                v.append(f"cut accepted a bad EDL: {edl}")
    return v


def python_stdio(server_py: Path, root: Path) -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=[str(server_py), str(root)])


def ts_stdio(entry: Path, root: Path) -> StdioServerParameters:
    return StdioServerParameters(
        command="node", args=["--experimental-strip-types", "--no-warnings", str(entry), str(root)]
    )


def binary_stdio(binary: Path, root: Path) -> StdioServerParameters:
    return StdioServerParameters(command=str(binary), args=[str(root)])


async def run_all(server: Any, mode: str = "auto") -> tuple[Report, list[str]]:
    async with Client(server, mode=mode) as c:  # type: ignore[arg-type]
        return await check_contract(c, TONE), await check_extended(c)
