from collections.abc import Callable
from typing import Any

from mcp import Client

SAMPLE_ARGS: dict[str, dict[str, Any]] = {"probe": {"path": "talk.mp4"}}
DESTRUCTIVE_PREFIXES = ("delete_", "remove_", "drop_")


async def contract_violations(client: Client) -> list[str]:
    problems: list[str] = []
    for tool in (await client.list_tools()).tools:
        if not (tool.description or "").strip():
            problems.append(f"{tool.name}: no description")
        if tool.name.startswith(DESTRUCTIVE_PREFIXES) and not (
            tool.annotations and tool.annotations.destructive_hint is True
        ):
            problems.append(f"{tool.name}: destructive without destructiveHint")
        if tool.name in SAMPLE_ARGS:
            try:
                result = await client.call_tool(tool.name, SAMPLE_ARGS[tool.name])
            except Exception:  # protocol error, or output failed outputSchema validation
                problems.append(f"{tool.name}: sample call failed")
                continue
            if result.is_error:
                problems.append(f"{tool.name}: sample call failed")
    return sorted(problems)


async def check_both(make_server: Callable[[], Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for mode in ("auto", "legacy"):
        async with Client(make_server(), mode=mode) as c:
            out[str(c.session.protocol_version)] = await contract_violations(c)
    return out
