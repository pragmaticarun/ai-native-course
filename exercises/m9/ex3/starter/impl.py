from collections.abc import Callable
from typing import Any

from mcp import Client

SAMPLE_ARGS: dict[str, dict[str, Any]] = {"probe": {"path": "talk.mp4"}}


async def contract_violations(client: Client) -> list[str]:
    # TODO
    return []


async def check_both(make_server: Callable[[], Any]) -> dict[str, list[str]]:
    # TODO: one run per revision
    async with Client(make_server()) as c:
        return {str(c.session.protocol_version): await contract_violations(c)}
