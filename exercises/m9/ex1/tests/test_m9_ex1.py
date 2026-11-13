import asyncio
from typing import Literal

import mcp_types as t
import pytest
from _impl import load
from mcp import Client

impl = load(__file__)


def answering(action: Literal["accept", "decline", "cancel"], confirm: bool = True):
    asked: list[str] = []

    async def cb(ctx, params):
        asked.append(params.message)
        if action == "accept":
            return t.ElicitResult(action="accept", content={"confirm": confirm})
        return t.ElicitResult(action=action)

    return cb, asked


async def call(
    mode: Literal["auto", "legacy"],
    action: Literal["accept", "decline", "cancel"],
    confirm: bool = True,
):
    published: list[tuple[str, str]] = []
    cb, asked = answering(action, confirm)
    async with Client(impl.build_server(published), elicitation_callback=cb, mode=mode) as c:
        r = await c.call_tool("publish", {"video_id": "v42", "channel": "main"})
    block = r.content[0]
    assert isinstance(block, t.TextContent)
    return block.text, asked, published


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_publishes_only_after_yes(mode):
    text, asked, published = asyncio.run(call(mode, "accept"))
    assert asked == ["Publish v42 to main?"]
    assert text == "published v42 to main" and published == [("v42", "main")]


@pytest.mark.parametrize("mode", ["auto", "legacy"])
@pytest.mark.parametrize("action,confirm", [("accept", False), ("decline", True), ("cancel", True)])
def test_anything_else_cancels(mode, action, confirm):
    text, asked, published = asyncio.run(call(mode, action, confirm))
    assert asked and text == "cancelled" and published == []


def test_new_revision_returns_input_required():
    async def go():
        cb, _ = answering("accept")
        async with Client(impl.build_server([]), elicitation_callback=cb) as c:
            assert c.session.protocol_version == "2026-07-28"
            tools = (await c.list_tools()).tools
            raw = await c.session.call_tool(
                "publish", {"video_id": "v1", "channel": "x"}, allow_input_required=True
            )
            return tools, raw

    tools, raw = asyncio.run(go())
    assert raw.result_type == "input_required" and len(raw.input_requests) == 1
    ann = tools[0].annotations
    assert ann is not None and ann.destructive_hint is True and ann.read_only_hint is not True
    assert set(tools[0].input_schema["properties"]) == {"video_id", "channel"}
