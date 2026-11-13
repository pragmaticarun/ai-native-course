import os

import pytest
from hello_agent import hello
from hello_pydantic_ai import make_agent

from aincourse import ScriptedModel, get_model


def test_hello_uses_mock_by_default():
    assert hello("Ada") == "Hello, Ada! (mock model, no network used)"


def test_get_model_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COURSE_LLM_PROVIDER", "nope")
    monkeypatch.setenv("COURSE_LLM_MODEL", "x")
    with pytest.raises(RuntimeError, match="Unknown COURSE_LLM_PROVIDER"):
        get_model()


def test_live_mode_requires_model_id(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COURSE_LLM_PROVIDER", "openai")
    monkeypatch.delenv("COURSE_LLM_MODEL", raising=False)
    with pytest.raises(RuntimeError, match="COURSE_LLM_MODEL"):
        get_model()


def test_default_is_scripted():
    assert os.environ["COURSE_LLM_PROVIDER"] == "mock"
    assert isinstance(get_model(), ScriptedModel)


def test_pydantic_ai_test_model():
    assert make_agent().run_sync("hi").output == "Hello from TestModel"
