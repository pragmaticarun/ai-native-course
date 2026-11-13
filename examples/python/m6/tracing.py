"""L6.5: OpenTelemetry traces for an agent run.

One trace per run: an `invoke_agent` span, a child span per model call (`chat`)
and per tool call (`execute_tool`). Attribute names follow the OpenTelemetry
GenAI semantic conventions (status: Development; they moved to
https://github.com/open-telemetry/semantic-conventions-genai, checked 13 Nov 2026):
gen_ai.operation.name, gen_ai.request.model, gen_ai.usage.input_tokens,
gen_ai.usage.output_tokens, gen_ai.tool.name, gen_ai.agent.name.

Here spans go to an in-memory exporter so tests can inspect them. In production
you'd export OTLP to Logfire, Phoenix, LangSmith, Jaeger, etc. (not exercised here).
What NOT to log by default: full prompts and tool outputs (PII, secrets). Log
sizes and ids, and opt in to content capture per environment.
"""

from __future__ import annotations

import json

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from aincourse import ChatModel, Message, ToolCall


def make_tracer() -> tuple[TracerProvider, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


def traced_run(
    provider: TracerProvider,
    model: ChatModel,
    model_name: str,
    tools: dict,
    task: str,
    max_steps: int = 5,
) -> str | None:
    tracer = provider.get_tracer("aincourse.m6")
    messages = [Message("user", task)]
    with tracer.start_as_current_span("invoke_agent explorer") as root:
        root.set_attribute("gen_ai.operation.name", "invoke_agent")
        root.set_attribute("gen_ai.agent.name", "explorer")
        for _ in range(max_steps):
            with tracer.start_as_current_span(f"chat {model_name}") as span:
                span.set_attribute("gen_ai.operation.name", "chat")
                span.set_attribute("gen_ai.request.model", model_name)
                turn = model.complete(messages)
                span.set_attribute("gen_ai.usage.input_tokens", turn.input_tokens)
                span.set_attribute("gen_ai.usage.output_tokens", turn.output_tokens)
            if not turn.tool_calls:
                root.set_attribute("aincourse.answer_chars", len(turn.text))
                return turn.text
            messages.append(turn.as_message())
            for call in turn.tool_calls:
                messages.append(
                    Message("tool", run_tool(tracer, tools, call), tool_call_id=call.id)
                )
        root.set_attribute("aincourse.stop_reason", "max_steps")
        return None


def run_tool(tracer, tools: dict, call: ToolCall) -> str:
    with tracer.start_as_current_span(f"execute_tool {call.name}") as span:
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("gen_ai.tool.name", call.name)
        span.set_attribute(
            "aincourse.args_chars", len(json.dumps(call.arguments))
        )  # size, not content
        try:
            out = str(tools[call.name](**call.arguments))
        except Exception as err:
            span.record_exception(err)
            span.set_attribute("error.type", type(err).__name__)
            out = f"error: {err}"
        span.set_attribute("aincourse.result_chars", len(out))
        return out
