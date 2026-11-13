"""STARTER. TODO: the spans.

P2 milestone 5: OpenTelemetry spans for every node.

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
            # TODO: run fn inside a span "p2.<name>" with node, topic, tokens, sim seconds
            return fn(state, *args, **kwargs)

        return inner

    return deco
