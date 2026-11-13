#!/usr/bin/env python3
"""Run every exercise against its solution (must pass) and starter (must fail).

Python exercises: exercises/mX/exY/tests/test_*.py, run with pytest.
TypeScript exercises: exercises/mX/exY/ts/*.test.ts, run with vitest.
Exit code is non-zero if any solution fails or any starter passes.
Use `--lang py` or `--lang ts` to check one language only.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], variant: str, cwd: Path) -> int:
    env = {**os.environ, "EXERCISE_VARIANT": variant, "COURSE_LLM_PROVIDER": "mock"}
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True).returncode


def main() -> int:
    langs = {"py", "ts"}
    if "--lang" in sys.argv:
        langs = {sys.argv[sys.argv.index("--lang") + 1]}
    problems: list[str] = []
    checked = 0
    for ex in sorted((ROOT / "exercises").glob("m*/ex*")):
        py_tests = sorted(ex.glob("tests/test_*.py"))
        ts_tests = sorted(ex.glob("ts/*.test.ts"))
        jobs: list[tuple[str, list[str], Path]] = []
        if py_tests and "py" in langs:
            jobs.append(
                (
                    "py",
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-q",
                        "-p",
                        "no:cacheprovider",
                        *map(str, py_tests),
                    ],
                    ROOT / "python",
                )
            )
        if ts_tests and "ts" in langs:
            jobs.append(("ts", ["npx", "vitest", "run", *map(str, ts_tests)], ROOT))
        for lang, cmd, cwd in jobs:
            checked += 1
            sol = run(cmd, "solution", cwd)
            start = run(cmd, "starter", cwd)
            rel = ex.relative_to(ROOT)
            status = "ok" if sol == 0 and start != 0 else "PROBLEM"
            print(f"{status:7s} {rel} [{lang}] solution_exit={sol} starter_exit={start}")
            if sol != 0:
                problems.append(f"{rel} [{lang}]: solution fails its tests")
            if start == 0:
                problems.append(f"{rel} [{lang}]: starter passes its tests (exercise is stale)")
    print(f"\n{checked} exercise test suites checked, {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
    return 1 if problems or checked == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
