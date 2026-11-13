"""Ex 11.1: find tests an agent weakened."""

from __future__ import annotations

import ast

BROAD = {"Exception", "BaseException"}


def _tests(src: str) -> dict[str, ast.FunctionDef]:
    return {
        n.name: n
        for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test")
    }


def _asserts(fn: ast.FunctionDef) -> list[ast.Assert]:
    return [n for n in ast.walk(fn) if isinstance(n, ast.Assert)]


def _is_eq(node: ast.expr) -> bool:
    return isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq)


def _expected(node: ast.expr) -> str:
    """The expected value, ignoring approx tolerances (checked separately)."""
    if isinstance(node, ast.Call) and ast.unparse(node.func).endswith("approx"):
        return ast.dump(ast.Tuple(elts=list(node.args), ctx=ast.Load()))
    return ast.dump(node)


def _tolerances(fn: ast.FunctionDef) -> list[float]:
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and ast.unparse(n.func).endswith("approx"):
            for kw in n.keywords:
                if (
                    kw.arg in {"abs", "rel"}
                    and isinstance(kw.value, ast.Constant)
                    and isinstance(kw.value.value, int | float)
                ):
                    out.append(float(kw.value.value))
    return out


def _raises(fn: ast.FunctionDef) -> list[str]:
    return [
        ast.unparse(n.args[0])
        for n in ast.walk(fn)
        if isinstance(n, ast.Call) and ast.unparse(n.func).endswith("raises") and n.args
    ]


def weakened_assertions(before: str, after: str) -> list[tuple[str, str]]:
    old, new = _tests(before), _tests(after)
    found: list[tuple[str, str]] = []
    for name, fn in old.items():
        if name not in new:
            continue
        kinds: list[str] = []
        a_old, a_new = _asserts(fn), _asserts(new[name])
        if len(a_new) < len(a_old):
            kinds.append("assert-deleted")
        for o, n in zip(a_old, a_new, strict=False):
            if _is_eq(o.test) and not isinstance(n.test, ast.Compare):
                kinds.append("equality-to-truthiness")
            elif _is_eq(o.test) and _is_eq(n.test):
                o_c, n_c = o.test, n.test
                assert isinstance(o_c, ast.Compare) and isinstance(n_c, ast.Compare)
                same_left = ast.dump(o_c.left) == ast.dump(n_c.left)
                if same_left and _expected(o_c.comparators[0]) != _expected(n_c.comparators[0]):
                    kinds.append("expected-changed")
        if any(n > o for o, n in zip(_tolerances(fn), _tolerances(new[name]), strict=False)):
            kinds.append("tolerance-widened")
        if any(
            o not in BROAD and n in BROAD
            for o, n in zip(_raises(fn), _raises(new[name]), strict=False)
        ):
            kinds.append("exception-broadened")
        found += [(name, k) for k in dict.fromkeys(kinds)]
    return found
