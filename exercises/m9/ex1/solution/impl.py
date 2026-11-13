from typing import Annotated

from mcp.server.mcpserver import AcceptedElicitation, Elicit, ElicitationResult, MCPServer, Resolve
from mcp_types import ToolAnnotations
from pydantic import BaseModel


class Confirm(BaseModel):
    confirm: bool


def ask(video_id: str, channel: str) -> Elicit[Confirm]:
    return Elicit(f"Publish {video_id} to {channel}?", Confirm)


def build_server(published: list[tuple[str, str]]) -> MCPServer:
    srv = MCPServer("publisher")

    @srv.tool(annotations=ToolAnnotations(destructive_hint=True, read_only_hint=False))
    def publish(
        video_id: str, channel: str, answer: Annotated[ElicitationResult[Confirm], Resolve(ask)]
    ) -> str:
        """Publish a video to a channel. Always asks the user first."""
        if isinstance(answer, AcceptedElicitation) and answer.data.confirm:
            published.append((video_id, channel))
            return f"published {video_id} to {channel}"
        return "cancelled"

    return srv
