"""L2.4: the same unit converter with Pydantic AI. FunctionModel plays the LLM."""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from unit_converter_raw import convert as _convert


def fake_llm(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    for part in messages[-1].parts:
        if isinstance(part, ToolReturnPart):
            return ModelResponse(parts=[TextPart(f"That is {part.content} miles.")])
    return ModelResponse(
        parts=[ToolCallPart("convert", {"value": 42.195, "from_unit": "km", "to_unit": "mi"})]
    )


def make_agent(model: FunctionModel | str | None = None) -> Agent[None, str]:
    agent = Agent(
        model or FunctionModel(fake_llm), instructions="Use the convert tool for unit conversions."
    )

    @agent.tool_plain
    def convert(value: float, from_unit: str, to_unit: str) -> float:
        """Convert a value between units. Supported: km<->mi, kg<->lb."""
        return _convert(value, from_unit, to_unit)

    return agent


if __name__ == "__main__":
    print(make_agent().run_sync("How many miles is a marathon?").output)
