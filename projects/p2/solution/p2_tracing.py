"""P2 milestone 5: OpenTelemetry spans for every node.

Each node runs inside a span named `p2.<node>` with the thread id, the node's simulated
model seconds and tokens as attributes. Tests export to memory; in production you'd swap
the exporter for OTLP (Jaeger, Tempo, Logfire, ...), which this course doesn't run.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Tracer


def memory_tracer() -> tuple[Tracer, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("p2-research"), exporter


def traced(
    tracer: Tracer, name: str, usage: Any
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:  # noqa: E501
    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def inner(state: Any, *args: Any, **kwargs: Any) -> Any:
            before_s, before_t = usage.sim_seconds, usage.tokens_in + usage.tokens_out
            with tracer.start_as_current_span(f"p2.{name}") as span:
                out = fn(state, *args, **kwargs)
                span.set_attribute("p2.node", name)
                if isinstance(state, dict) and "topic" in state:
                    span.set_attribute("p2.topic", state["topic"])
                # Parallel workers share one Usage, so these deltas are approximate for them.
                span.set_attribute("p2.sim_seconds", round(usage.sim_seconds - before_s, 3))
                span.set_attribute("p2.tokens", usage.tokens_in + usage.tokens_out - before_t)
                return out

        return inner

    return deco
