"""L8.3: a durable Pydantic AI agent on Temporal (`TemporalDurability` capability).

Inside a workflow, the agent's model requests and tool calls become Temporal activities,
so a crash mid-run resumes without re-asking the model or re-running finished tools.
Outside a workflow the same `Agent` behaves normally. The model here is a `FunctionModel`
(deterministic, offline); with a real provider you would pass a model name instead.
Tested with pydantic-ai-slim 2.68.0 and temporalio 1.36.0 (time-skipping test server).
"""

from __future__ import annotations

import uuid

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import (
    PydanticAIPlugin,
    PydanticAIWorkflow,
    TemporalDurability,
)
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

TOOL_CALLS: list[str] = []  # tool executions, visible to tests (activities run in-process here)


def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    returns = [
        p for m in messages for p in getattr(m, "parts", []) if isinstance(p, ToolReturnPart)
    ]
    if not returns:
        return ModelResponse(parts=[ToolCallPart("probe", {"path": "talk.mp4"})])
    return ModelResponse(parts=[TextPart(f"The recording is {returns[-1].content}.")])


agent = Agent(FunctionModel(scripted), name="media_agent", capabilities=[TemporalDurability()])


@agent.tool_plain
def probe(path: str) -> str:
    """Return the duration of a media file."""
    TOOL_CALLS.append(path)
    return "7200 seconds long"


@workflow.defn
class MediaQuestion(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [agent]

    @workflow.run
    async def run(self, prompt: str) -> str:
        result = await agent.run(prompt)
        return result.output


async def ask(env_client: Client, prompt: str) -> str:
    cfg = env_client.config()
    cfg["plugins"] = [PydanticAIPlugin()]
    client = Client(**cfg)
    async with Worker(client, task_queue="m8-pydantic-ai", workflows=[MediaQuestion]):
        return await client.execute_workflow(
            MediaQuestion.run, prompt, id=f"mq-{uuid.uuid4().hex[:8]}", task_queue="m8-pydantic-ai"
        )
