from collections.abc import Mapping
from typing import NamedTuple


class ProviderConfig(NamedTuple):
    provider: str
    model: str | None
    key_var: str | None


def resolve_provider(env: Mapping[str, str]) -> ProviderConfig:
    # TODO: read COURSE_LLM_PROVIDER / COURSE_LLM_MODEL and validate the key variable.
    return ProviderConfig("mock", None, None)
