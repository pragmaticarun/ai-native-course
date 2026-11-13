"""P3 milestone 4: OAuth on the Streamable HTTP transport (resource-server side).

The MCP server doesn't issue tokens; an authorization server does. The server's job is to
(1) refuse requests without a valid bearer token, pointing clients at its protected-resource
metadata, (2) accept only tokens issued *for this server* (the RFC 8707 resource), and
(3) check scopes per tool. `StaticTokenVerifier` stands in for token introspection or JWT
validation against a real authorization server (not run in this course).
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import uvicorn
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from p3_server import build_server

ISSUER = "https://auth.example.com"


class StaticTokenVerifier:
    """token -> AccessToken. Unknown tokens verify to None (401)."""

    def __init__(self, tokens: dict[str, AccessToken]) -> None:
        self.tokens = tokens

    async def verify_token(self, token: str) -> AccessToken | None:
        tok = self.tokens.get(token)
        if tok is None or (tok.expires_at is not None and tok.expires_at < time.time()):
            return None
        return tok


def auth_kwargs(verifier: StaticTokenVerifier, resource_url: str) -> dict[str, Any]:
    return {
        "auth": AuthSettings(
            issuer_url=ISSUER,  # type: ignore[arg-type]
            resource_server_url=resource_url,  # type: ignore[arg-type]
            required_scopes=["media:read"],
            validate_token_resource=True,
        ),
        "token_verifier": verifier,
    }


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@contextmanager
def serve_http(root: Path, verifier: StaticTokenVerifier) -> Iterator[str]:
    """Run the toolkit over Streamable HTTP on localhost in a thread; yield the MCP URL."""
    port = free_port()
    url = f"http://127.0.0.1:{port}/mcp"
    app = build_server(root, **auth_kwargs(verifier, url)).streamable_http_app()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    try:
        yield url
    finally:
        server.should_exit = True
        t.join(timeout=5)
