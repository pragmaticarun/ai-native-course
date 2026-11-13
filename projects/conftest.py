"""Project evals: put the project's `common/` and the chosen variant (starter or solution,
from PROJECT_VARIANT, default solution) on sys.path, plus the worked examples."""

import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
os.environ["COURSE_LLM_PROVIDER"] = "mock"
for module_dir in sorted((HERE.parent / "examples" / "python").glob("m*")):
    sys.path.insert(0, str(module_dir))


def pytest_configure(config):
    variant = os.environ.get("PROJECT_VARIANT", "solution")
    if variant not in {"starter", "solution"}:
        raise ValueError(f"PROJECT_VARIANT must be starter or solution, not {variant!r}")
    for arg in config.args:
        p = Path(arg).resolve()
        proj = next((q for q in [p, *p.parents] if q.parent == HERE), None)
        if proj is not None:
            sys.path.insert(0, str(proj / "common"))
            sys.path.insert(0, str(proj / variant))
