import asyncio

from _impl import load
from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations
from pydantic import BaseModel

impl = load(__file__)


class Probe(BaseModel):
    path: str
    duration_s: float


def good() -> MCPServer:
    srv = MCPServer("good")

    @srv.tool(annotations=ToolAnnotations(read_only_hint=True))
    def probe(path: str) -> Probe:
        """Probe a media file."""
        return Probe(path=path, duration_s=7200.0)

    @srv.tool(annotations=ToolAnnotations(destructive_hint=True))
    def delete_clip(path: str) -> str:
        """Delete a clip."""
        return "ok"

    return srv


def sloppy() -> MCPServer:
    srv = MCPServer("sloppy")

    @srv.tool(description="Probe a media file.")
    def probe(path: str) -> Probe:
        raise ValueError("ffprobe not found")  # works on the dev's laptop only

    @srv.tool(description="")
    def delete_clip(path: str) -> str:
        return "ok"

    @srv.tool(description="Drop an index.", annotations=ToolAnnotations(read_only_hint=False))
    def drop_index(name: str) -> str:
        return "ok"

    return srv


def test_good_server_passes_on_both_revisions():
    assert asyncio.run(impl.check_both(good)) == {"2026-07-28": [], "2025-11-25": []}


def test_sloppy_server():
    expected = [
        "delete_clip: destructive without destructiveHint",
        "delete_clip: no description",
        "drop_index: destructive without destructiveHint",
        "probe: sample call failed",
    ]
    assert asyncio.run(impl.check_both(sloppy)) == {"2026-07-28": expected, "2025-11-25": expected}
