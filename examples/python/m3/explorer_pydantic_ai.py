"""L3.3: the explorer agent in Pydantic AI. The step budget becomes UsageLimits."""

from __future__ import annotations

from pathlib import Path

from explorer_agent import make_tools
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.usage import UsageLimits


def fake_llm(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    returns = [p.content for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
    if not returns:
        return ModelResponse(parts=[ToolCallPart("grep", {"pattern": "def main", "path": "."})])
    path = str(returns[0]).split(":", 1)[0]
    return ModelResponse(parts=[TextPart(f"The entry point is main() in {path}.")])


def make_agent(root: Path, model: FunctionModel | str | None = None) -> Agent[None, str]:
    agent = Agent(
        model or FunctionModel(fake_llm),
        instructions="You explore a codebase with read-only tools.",
    )
    for tool in make_tools(root).values():
        agent.tool_plain(name=tool.spec.name, description=tool.spec.description)(tool.fn)
    return agent


def explore(root: Path, question: str, max_requests: int = 6) -> str:
    return (
        make_agent(root)
        .run_sync(question, usage_limits=UsageLimits(request_limit=max_requests))
        .output
    )


if __name__ == "__main__":
    print(explore(Path("."), "Where is the entry point?"))
