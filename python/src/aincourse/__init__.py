"""Shared helpers for the AI-native software development course.

Everything here is deliberately small so you can read it in one sitting.
"""

import os

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # keep example output clean

from aincourse.llm import (
    AssistantTurn,
    ChatModel,
    Message,
    ScriptedModel,
    ToolCall,
    ToolSpec,
    get_model,
)

__all__ = [
    "AssistantTurn",
    "ChatModel",
    "Message",
    "ScriptedModel",
    "ToolCall",
    "ToolSpec",
    "get_model",
]
