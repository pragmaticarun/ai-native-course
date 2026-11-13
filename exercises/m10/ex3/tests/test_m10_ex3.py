from pathlib import Path

from _impl import load

impl = load(__file__)
FIX = Path(__file__).parent / "fixtures"


def test_hostile_repo():
    assert impl.find_hostile(FIX / "hostile") == {
        "interactive-prompt": ["scripts/setup.sh"],
        "flaky-test": ["tests/test_api.py"],
        "swallowed-error": ["src/loader.py"],
    }


def test_clean_repo():
    assert impl.find_hostile(FIX / "clean") == {}


def test_git_dir_is_skipped(tmp_path):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / ".git" / "hooks" / "pre-commit.sh").write_text("read -p 'ok?' x\n")
    assert impl.find_hostile(tmp_path) == {}
