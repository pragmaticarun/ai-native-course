#!/usr/bin/env python3
"""Validate quizzes/*.yaml against quizzes/schema.json and check answer keys."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent


def check_answer(q: dict) -> str | None:
    n = len(q.get("choices", []))
    a: Any = q.get("answer")
    if q["type"] in ("single", "spot_bug"):
        ok = isinstance(a, int) and 0 <= a < n
    elif q["type"] == "multi":
        ok = isinstance(a, list) and bool(a) and len(set(a)) == len(a)
        ok = ok and all(0 <= i < n for i in a)
    else:  # order: a permutation of all choices
        ok = isinstance(a, list) and sorted(a) == list(range(n))
    return None if ok else f"{q['id']}: bad answer key {a!r} for {q['type']} with {n} choices"


def main() -> int:
    validator = Draft202012Validator(json.loads((ROOT / "quizzes/schema.json").read_text()))
    errors, total = [], 0
    ids: set[str] = set()
    for path in sorted((ROOT / "quizzes").glob("m*.yaml")):
        data = yaml.safe_load(path.read_text())
        errors += [f"{path.name}: {e.message}" for e in validator.iter_errors(data)]
        for q in data.get("questions", []):
            total += 1
            if q["id"] in ids:
                errors.append(f"duplicate id {q['id']}")
            ids.add(q["id"])
            if err := check_answer(q):
                errors.append(f"{path.name}: {err}")
    print(f"{total} questions checked, {len(errors)} error(s)")
    for e in errors:
        print("  -", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
