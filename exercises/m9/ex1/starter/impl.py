from mcp.server.mcpserver import MCPServer


def build_server(published: list[tuple[str, str]]) -> MCPServer:
    srv = MCPServer("publisher")

    @srv.tool()
    def publish(video_id: str, channel: str) -> str:
        """Publish a video to a channel."""
        # TODO: ask first (input_required / elicitation), annotate as destructive
        published.append((video_id, channel))
        return f"published {video_id} to {channel}"

    return srv
