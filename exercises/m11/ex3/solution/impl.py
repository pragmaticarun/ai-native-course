"""Ex 11.3: a mechanical review checklist for agent PRs."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

DEP_FILES = re.compile(r"(^|/)(pyproject\.toml|requirements[^/]*\.txt|package\.json)$")
RANGE = re.compile(r">=|~=|\^|~|\*|<=|(?<![=!<>])[<>](?!=)")


@dataclass
class PR:
    files: dict[str, str]  # path -> added lines
    deleted: list[str] = field(default_factory=list)


def tests_with_code(pr: PR) -> bool:
    code = any(p.startswith("src/") for p in pr.files)
    return not code or any(p.startswith("tests/") for p in pr.files)


def pinned_deps(pr: PR) -> bool:
    for path, text in pr.files.items():
        if DEP_FILES.search(path):
            for line in text.splitlines():
                if RANGE.search(line):
                    return False
    return True


def todo_has_issue(pr: PR) -> bool:
    lines = (ln for text in pr.files.values() for ln in text.splitlines())
    return all(re.search(r"#\d+", ln) for ln in lines if re.search(r"\b(TODO|FIXME)\b", ln))


def reversible_migration(pr: PR) -> bool:
    return all(
        "def downgrade" in text
        for path, text in pr.files.items()
        if path.startswith("migrations/") and "def upgrade" in text
    )


def no_deleted_tests(pr: PR) -> bool:
    return not any(p.startswith("tests/") for p in pr.deleted)


CHECKS: dict[str, Callable[[PR], bool]] = {
    "tests-with-code": tests_with_code,
    "pinned-deps": pinned_deps,
    "todo-has-issue": todo_has_issue,
    "reversible-migration": reversible_migration,
    "no-deleted-tests": no_deleted_tests,
}


def apply(pr: PR) -> dict[str, bool]:
    return {name: check(pr) for name, check in CHECKS.items()}
