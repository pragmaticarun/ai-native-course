"""Load an exercise implementation: the starter or the solution.

Tests call `load(__file__)`. EXERCISE_VARIANT=starter|solution picks which one
(default: solution). CI runs every test file against both and requires the
solution to pass and the starter to fail.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType


def load(test_file: str, module: str = "impl") -> ModuleType:
    variant = os.environ.get("EXERCISE_VARIANT", "solution")
    if variant not in {"starter", "solution"}:
        raise ValueError(f"EXERCISE_VARIANT must be starter or solution, not {variant!r}")
    path = Path(test_file).resolve().parent.parent / variant / f"{module}.py"
    spec = importlib.util.spec_from_file_location(
        f"{path.parents[2].name}_{path.parent.parent.name}_{variant}", path
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses look their module up here
    spec.loader.exec_module(mod)
    return mod


def variant_dir(test_file: str) -> Path:
    """The starter/ or solution/ directory, for exercises whose answer is a file, not code."""
    variant = os.environ.get("EXERCISE_VARIANT", "solution")
    return Path(test_file).resolve().parent.parent / variant
