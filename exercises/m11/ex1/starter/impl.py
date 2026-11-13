"""Ex 11.1: find tests an agent weakened."""

from __future__ import annotations

import ast


def _tests(src: str) -> dict[str, ast.FunctionDef]:
    return {
        n.name: n
        for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test")
    }


def _asserts(fn: ast.FunctionDef) -> list[ast.Assert]:
    return [n for n in ast.walk(fn) if isinstance(n, ast.Assert)]


def weakened_assertions(before: str, after: str) -> list[tuple[str, str]]:
    old, new = _tests(before), _tests(after)
    found = []
    for name, fn in old.items():
        if name in new and len(_asserts(new[name])) < len(_asserts(fn)):
            found.append((name, "assert-deleted"))
        # TODO: equality-to-truthiness, expected-changed, tolerance-widened, exception-broadened
    return found
