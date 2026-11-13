"""Ex 10.3: report agent-hostile traits in a repository."""

from __future__ import annotations

import re
from pathlib import Path

SHELL_READ = re.compile(r"(?:^|[;&|])\s*read\s+\S", re.M)  # `read` as a command, not in prose
PY_INPUT = re.compile(r"\binput\(")
SLEEP = re.compile(r"\b(time\.)?sleep\(")
NETWORK = re.compile(r"https?://")
SWALLOWED = re.compile(r"^\s*except(\s+Exception)?\s*:\s*\n\s*pass\b", re.M)


def _flaky(text: str) -> bool:
    unseeded = "random." in text and "random.seed(" not in text
    return bool(SLEEP.search(text) or NETWORK.search(text) or unseeded)


def find_hostile(repo: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}

    def add(trait: str, path: Path) -> None:
        found.setdefault(trait, []).append(path.relative_to(repo).as_posix())

    for path in sorted(repo.rglob("*")):
        if ".git" in path.parts or path.suffix not in {".sh", ".py"} or not path.is_file():
            continue
        text = path.read_text(errors="replace")
        code = re.sub(r"(^|\s)#.*", "", text) if path.suffix == ".sh" else text  # drop comments
        if (SHELL_READ if path.suffix == ".sh" else PY_INPUT).search(code):
            add("interactive-prompt", path)
        if path.name.startswith("test_") and _flaky(text):
            add("flaky-test", path)
        if SWALLOWED.search(text):
            add("swallowed-error", path)
    return {k: sorted(v) for k, v in found.items()}
