import pytest
from _impl import load

impl = load(__file__)


def test_default_is_mock():
    assert impl.resolve_provider({}) == ("mock", None, None)


def test_live_provider_normalised():
    env = {"COURSE_LLM_PROVIDER": " OpenAI ", "COURSE_LLM_MODEL": "m1", "OPENAI_API_KEY": "sk-x"}
    assert impl.resolve_provider(env) == ("openai", "m1", "OPENAI_API_KEY")


@pytest.mark.parametrize(
    "env",
    [
        {"COURSE_LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "k"},  # no model
        {"COURSE_LLM_PROVIDER": "anthropic", "COURSE_LLM_MODEL": "m"},  # no key
        {"COURSE_LLM_PROVIDER": "llamas", "COURSE_LLM_MODEL": "m"},  # unknown
    ],
)
def test_invalid_configs_raise(env):
    with pytest.raises(ValueError):
        impl.resolve_provider(env)


def test_error_never_leaks_key():
    env = {"COURSE_LLM_PROVIDER": "openai", "COURSE_LLM_MODEL": "", "OPENAI_API_KEY": "sk-secret"}
    with pytest.raises(ValueError) as err:
        impl.resolve_provider(env)
    assert "sk-secret" not in str(err.value)
