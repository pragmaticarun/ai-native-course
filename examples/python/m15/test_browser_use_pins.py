"""Checks browser_use_notes against the real browser-use 1.0.6 package.

Skipped unless browser-use is installed: its exact pins (e.g. pydantic-ai-slim 2.66.0) conflict
with the course lock, so CI runs this file in an isolated env:
    uv run --isolated --no-project --with browser-use==1.0.6 --with pytest==9.2.0 \\
        pytest -c ../pytest.ini ../examples/python/m15/test_browser_use_pins.py
Nothing here constructs an Agent or calls a model (no key, no network).
"""

import importlib.metadata
import inspect
import json
import os
from pathlib import Path

import browser_use_notes as bn
import pytest

if os.environ.get("M15_REQUIRE_BROWSER_USE"):
    import browser_use  # noqa: F401  (fail, don't skip, when CI asks for it)
browser_use = pytest.importorskip("browser_use")

from browser_use.agent import loop  # noqa: E402
from browser_use.agent.judge import Judgement  # noqa: E402
from browser_use.agent.views import AgentHistoryList  # noqa: E402
from browser_use.llm import DEFAULT_MODEL, ChatBrowserUse  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "browser_use_judgements.json"


def test_installed_version_is_the_course_pin():
    assert importlib.metadata.version("browser-use") == "1.0.6"


def test_default_model_is_bu_4_0():
    assert DEFAULT_MODEL == bn.DEFAULT_LLM_1_0_6 == "bu-4.0"
    assert inspect.signature(ChatBrowserUse.__init__).parameters["model"].default == "bu-4.0"
    assert inspect.signature(browser_use.Agent.__init__).parameters["llm"].default is None


def test_judge_options_and_result_field_exist():
    params = inspect.signature(browser_use.Agent.__init__).parameters
    assert params["judge"].default is True and params["judge_context"].default is None
    assert "judgement" in AgentHistoryList.__dataclass_fields__
    assert tuple(Judgement.model_fields) == bn.JUDGEMENT_FIELDS


def test_fixture_judgements_validate_against_the_real_model():
    for name, data in json.loads(FIXTURE.read_text())["judgements"].items():
        assert Judgement.model_validate(data).model_dump() == data, name


def test_batch_screenshot_pruning_constants():
    assert (loop.PRUNE_IMAGES_AT, loop.KEEP_IMAGE_RESULTS) == (
        bn.PRUNE_IMAGES_AT,
        bn.KEEP_IMAGE_RESULTS,
    )
