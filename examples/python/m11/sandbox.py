"""Shared helper for M11: a throwaway git repo with a tiny Python project and its tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

CLIP = '''def trim(duration_s: float, start_s: float, end_s: float) -> float:
    """Length of the clip between start and end, clamped to the media."""
    return end_s - start_s
'''

TESTS = """from clip import trim


def test_inside():
    assert trim(60, 10, 20) == 10


def test_clamps_end_to_duration():
    assert trim(60, 50, 90) == 10


def test_rejects_reversed():
    import pytest

    with pytest.raises(ValueError):
        trim(60, 20, 10)
"""


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout


def make_sandbox(root: Path) -> Path:
    repo = root / "clip-tools"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "clip.py").write_text(CLIP)
    (repo / "tests" / "test_clip.py").write_text(TESTS)
    (repo / ".gitignore").write_text("__pycache__/\n")
    (repo / "pytest.ini").write_text("[pytest]\npythonpath = src\naddopts = -p no:cacheprovider\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "dev@example.com")
    git(repo, "config", "user.name", "dev")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "initial")
    return repo


def pytest_run(repo: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *extra],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
