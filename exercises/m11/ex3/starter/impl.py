"""Ex 11.3: a mechanical review checklist for agent PRs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class PR:
    files: dict[str, str]  # path -> added lines
    deleted: list[str] = field(default_factory=list)


def tests_with_code(pr: PR) -> bool:
    return True  # TODO


def pinned_deps(pr: PR) -> bool:
    return True  # TODO


def todo_has_issue(pr: PR) -> bool:
    return True  # TODO


def reversible_migration(pr: PR) -> bool:
    return True  # TODO


def no_deleted_tests(pr: PR) -> bool:
    return True  # TODO


CHECKS: dict[str, Callable[[PR], bool]] = {
    "tests-with-code": tests_with_code,
    "pinned-deps": pinned_deps,
    "todo-has-issue": todo_has_issue,
    "reversible-migration": reversible_migration,
    "no-deleted-tests": no_deleted_tests,
}


def apply(pr: PR) -> dict[str, bool]:
    return {name: check(pr) for name, check in CHECKS.items()}
