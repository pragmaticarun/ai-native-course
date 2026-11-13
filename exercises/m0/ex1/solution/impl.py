from collections.abc import Mapping
from typing import NamedTuple

KEY_VARS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


class ProviderConfig(NamedTuple):
    provider: str
    model: str | None
    key_var: str | None


def resolve_provider(env: Mapping[str, str]) -> ProviderConfig:
    provider = env.get("COURSE_LLM_PROVIDER", "").strip().lower()
    if provider in ("", "mock"):
        return ProviderConfig("mock", None, None)
    if provider not in KEY_VARS:
        raise ValueError(f"unknown provider {provider!r}; use one of mock, {', '.join(KEY_VARS)}")
    model = env.get("COURSE_LLM_MODEL", "").strip()
    if not model:
        raise ValueError("COURSE_LLM_MODEL is required for live providers")
    key_var = KEY_VARS[provider]
    if not env.get(key_var, "").strip():
        raise ValueError(f"{key_var} is not set")  # name only, never the value
    return ProviderConfig(provider, model, key_var)
