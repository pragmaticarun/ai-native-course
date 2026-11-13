"""M9 L9.5: one contract, many servers.

`check_contract` is a list of promises any "media-probe" server must keep, whatever its
language or transport. It runs through the Python MCP client in either protocol mode:
`mode="auto"` negotiates the 2026-07-28 stateless revision when the server offers it,
`mode="legacy"` forces the 2025-11-25 handshake. Servers checked in this repo:

* the Python server in-process (fixture runner, no ffmpeg needed);
* the Python server as a subprocess over stdio (real ffprobe/ffmpeg);
* the TypeScript server over stdio via Node (real ffprobe/ffmpeg), when node_modules exist;
* the Rust rmcp server binary over stdio (real ffprobe/ffmpeg), when built.

The Kotlin server is checked by its own Kotlin tests (kmp/), not from here.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters
from mcp.shared.exceptions import MCPError

REQUIRED_TOOLS = ("probe", "loudness")


@dataclass
class Expect:
    file: str  # relative to the server's media root
    duration_s: float
    tolerance_s: float = 0.05
    stream_types: tuple[str, ...] = ("audio",)


@dataclass
class Report:
    protocol_version: str
    tools: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


def _payload(result: Any) -> dict[str, Any] | None:
    if result.structured_content is not None:
        return dict(result.structured_content)
    import json

    try:
        return dict(json.loads(result.content[0].text))
    except (ValueError, IndexError, AttributeError):
        return None


async def check_contract(client: Client, expect: Expect) -> Report:
    rep = Report(protocol_version=str(client.session.protocol_version))
    v = rep.violations
    tools = {t.name: t for t in (await client.list_tools()).tools}
    rep.tools = sorted(tools)
    for name in REQUIRED_TOOLS:
        t = tools.get(name)
        if t is None:
            v.append(f"missing tool {name}")
            continue
        if not (t.description or "").strip():
            v.append(f"{name}: no description")
        if t.annotations is None or t.annotations.read_only_hint is not True:
            v.append(f"{name}: not annotated read_only_hint=true")
        if not t.output_schema:
            v.append(f"{name}: no outputSchema")
        if "path" not in (t.input_schema.get("properties") or {}):
            v.append(f"{name}: input has no 'path'")
    if v:
        return rep

    probe = await client.call_tool("probe", {"path": expect.file})
    data = _payload(probe)
    if probe.is_error or data is None:
        v.append(f"probe failed: {probe.content}")
    else:
        if abs(float(data.get("duration_s", -1)) - expect.duration_s) > expect.tolerance_s:
            v.append(f"probe duration {data.get('duration_s')} != {expect.duration_s}")
        kinds = {s.get("codec_type") for s in data.get("streams", [])}
        if not set(expect.stream_types) <= kinds:
            v.append(f"probe streams {sorted(kinds)} missing {expect.stream_types}")

    loud = await client.call_tool("loudness", {"path": expect.file})
    ldata = _payload(loud)
    if loud.is_error or ldata is None:
        v.append(f"loudness failed: {loud.content}")
    elif not all(math.isfinite(float(ldata[k])) for k in ("integrated_lufs", "true_peak_dbtp")):
        v.append(f"loudness not finite: {ldata}")

    for bad in ("../secret.wav", "/etc/passwd"):
        r = await client.call_tool("probe", {"path": bad})
        if not r.is_error:
            v.append(f"path escape not refused: {bad}")
    # The spec lists an unknown tool as a protocol error (JSON-RPC error); some servers
    # return an is_error tool result instead. Either is a refusal; success is not.
    try:
        r = await client.call_tool("no_such_tool", {})
        if not r.is_error:
            v.append("unknown tool call succeeded")
    except MCPError:
        pass
    return rep


def python_stdio(root: Path) -> StdioServerParameters:
    here = Path(__file__).with_name("media_probe_server.py")
    return StdioServerParameters(command=sys.executable, args=[str(here), str(root)])


def ts_stdio(root: Path) -> StdioServerParameters:
    entry = Path(__file__).resolve().parents[2] / "ts" / "m9" / "mediaProbeStdio.ts"
    return StdioServerParameters(
        command="node", args=["--experimental-strip-types", "--no-warnings", str(entry), str(root)]
    )


def binary_stdio(binary: Path, root: Path) -> StdioServerParameters:
    return StdioServerParameters(command=str(binary), args=[str(root)])


async def run(server: Any, expect: Expect, mode: str = "auto", **client_kwargs: Any) -> Report:
    async with Client(server, mode=mode, **client_kwargs) as c:  # type: ignore[arg-type]
        return await check_contract(c, expect)
