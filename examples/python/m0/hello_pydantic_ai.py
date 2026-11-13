"""M0: the same hello, through Pydantic AI's built-in TestModel (no network)."""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel


def make_agent() -> Agent[None, str]:
    # TestModel returns deterministic output; swap in a real model id for live runs.
    return Agent(TestModel(custom_output_text="Hello from TestModel"), instructions="Be terse.")


if __name__ == "__main__":
    print(make_agent().run_sync("Say hello").output)
