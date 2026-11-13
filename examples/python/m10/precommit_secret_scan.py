#!/usr/bin/env python3
"""A git pre-commit hook: refuse the commit if a staged file looks like it has a secret.

Install:  ln -s ../../examples/python/m10/precommit_secret_scan.py .git/hooks/pre-commit
(Agents run the same hooks as humans when they commit, so this catches both.)
In production use a maintained scanner (e.g. gitleaks) via the pre-commit framework.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hooks import scan_secrets  # noqa: E402


def main() -> int:
    names = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    found = []
    for name in names:
        staged = subprocess.run(["git", "show", f":{name}"], capture_output=True, text=True).stdout
        found += [f"{name}:{line}: {kind}" for line, kind in scan_secrets(staged)]
    if found:
        print(
            "pre-commit: possible secrets, commit refused:\n  " + "\n  ".join(found),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
