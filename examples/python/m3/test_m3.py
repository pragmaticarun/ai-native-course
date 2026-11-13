from pathlib import Path

import computer_use_sim as cu
import pytest
from explorer_agent import explore, make_tools
from explorer_pydantic_ai import explore as explore_pai
from failure_modes import hallucinated_tools, premature_done, repeated_calls
from mobile_adb import AdbDevice, parse_ui, render_for_model
from scratch_loop import Tool, run_agent

from aincourse import AssistantTurn, ScriptedModel, ToolCall, ToolSpec

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("import sys\n\ndef main():\n    print('hi')\n")
    (tmp_path / "README.md").write_text("demo\n")
    return tmp_path


def test_explorer_answers_from_observations(repo: Path):
    result = explore(repo, "Where is the entry point?")
    assert result.stop_reason == "answered"
    assert result.answer == "The entry point is main() in src/app.py."
    assert result.steps == 3


def test_explorer_admits_no_match(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("nothing here")
    assert explore(tmp_path, "entry?").answer == "I found no `def main` in this tree."


def test_explorer_pydantic_ai(repo: Path):
    assert explore_pai(repo, "entry?") == "The entry point is main() in src/app.py."


def test_sandbox_blocks_traversal(repo: Path):
    tools = make_tools(repo)
    with pytest.raises(PermissionError):
        tools["read_file"].fn("../../etc/passwd")


def test_errors_are_observations_and_budget_stops(repo: Path):
    calls = [
        AssistantTurn(tool_calls=(ToolCall("read_file", {"path": f"missing{i}"}, f"c{i}"),))
        for i in range(10)
    ]
    result = run_agent(ScriptedModel(calls), make_tools(repo), "loop forever", max_steps=4)
    assert result.stop_reason == "max_steps" and result.steps == 4
    assert all("error: FileNotFoundError" in t for t in result.trace)


def test_repetition_stop_and_hallucinated_tool():
    same = AssistantTurn(tool_calls=(ToolCall("nope", {"a": 1}),))
    echo = Tool(ToolSpec("echo", "echo", {"type": "object"}), lambda **kw: kw)
    result = run_agent(ScriptedModel([same] * 10), {"echo": echo}, "x", max_repeats=2)
    assert result.stop_reason == "repetition"
    assert "no tool named 'nope'" in result.trace[0]


def test_failure_detectors():
    c = ToolCall("read", {"p": 1})
    assert repeated_calls([c, c, c, ToolCall("x", {})]) == ['read:{"p": 1}']
    assert hallucinated_tools([c, ToolCall("ghost", {})], {"read"}) == ["ghost"]
    assert premature_done(True, False) and not premature_done(True, True)


def test_vendor_adapters_map_to_same_action():
    anthropic = {
        "type": "tool_use",
        "id": "toolu_1",
        "name": "left_click",
        "toolset_name": "computer",
        "input": {"coordinate": [512, 742]},
    }
    openai = {"type": "click", "button": "left", "x": 512, "y": 742}
    assert cu.from_anthropic(anthropic) == cu.from_openai(openai) == cu.Action("click", 512, 742)
    assert cu.from_anthropic(
        {"name": "type", "toolset_name": "computer", "input": {"text": "hi"}}
    ) == cu.from_openai({"type": "type", "text": "hi"})
    assert cu.from_openai({"type": "keypress", "keys": ["CTRL", "S"]}).text == "CTRL+S"
    with pytest.raises(ValueError):
        cu.from_anthropic({"name": "left_click", "input": {}})  # missing toolset_name


def test_naive_agent_claims_done_but_fails_after_layout_shift():
    screen = cu.FormScreen(layout_shift=True)
    claimed, _ = cu.run(screen, cu.naive_policy("Ada", "ada@example.com"))
    assert claimed and not cu.task_succeeded(screen, "Ada", "ada@example.com")
    assert premature_done(claimed, cu.task_succeeded(screen, "Ada", "ada@example.com"))


def test_careful_agent_succeeds_after_layout_shift():
    screen = cu.FormScreen(layout_shift=True)
    claimed, steps = cu.run(screen, cu.careful_policy("Ada", "ada@example.com"))
    assert claimed and cu.task_succeeded(screen, "Ada", "ada@example.com")
    assert steps <= 4


def test_adb_parsing_and_commands():
    xml = (FIXTURES / "login_screen.xml").read_text()
    nodes = parse_ui(xml)
    assert [n.text for n in nodes] == ["Welcome", "Username", "Sign in"]
    assert render_for_model(nodes).splitlines()[2] == "[3] button 'Sign in'"
    sent: list[list[str]] = []

    def fake(args):
        sent.append(list(args))
        return xml.encode() if "exec-out" in args and args[-1] == "/sdcard/ui.xml" else b""

    dev = AdbDevice(fake, serial="emulator-5554")
    tree = dev.ui_tree()
    dev.tap(tree[2])
    dev.type_text("hello world")
    assert sent[-2] == ["-s", "emulator-5554", "shell", "input", "tap", "540", "1300"]
    assert sent[-1][-1] == "hello%sworld"
