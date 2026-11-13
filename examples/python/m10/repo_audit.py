"""M10 L10.5: a structural audit of how agent-friendly a repository is.

Each check is something an agent needs and can't infer reliably: where the
instructions are, the one command that says "done", pinned dependencies, typed
interfaces and CI. This is the course's checklist, not a standard; the weights are
all 1 on purpose (argue about the checks, not the score).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

LOCKS = {
    "pyproject.toml": ("uv.lock", "poetry.lock", "pdm.lock"),
    "package.json": ("pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lock"),
    "Cargo.toml": ("Cargo.lock",),
    "go.mod": ("go.sum",),
}


def _text(p: Path) -> str:
    return p.read_text(errors="replace") if p.is_file() else ""


def _manifests(repo: Path) -> list[Path]:
    skip = {"node_modules", "target", ".git", "fixtures", ".venv"}
    return [
        p for name in LOCKS for p in repo.rglob(name) if not skip & set(p.relative_to(repo).parts)
    ]


def audit(repo: Path) -> dict[str, bool]:
    instructions = _text(repo / "AGENTS.md") or _text(repo / "CLAUDE.md")
    makefile = _text(repo / "Makefile")
    checks = {
        "instructions-file": bool(instructions),
        "verify-command": bool(
            re.search(r"^verify:", makefile, re.M)
            or re.search(r"^Verify: `[^`]+`", instructions, re.M)
            or (repo / "verify.sh").is_file()
        ),
        "one-command-setup": bool(
            re.search(r"^setup:", makefile, re.M)
            or re.search(r"^Setup: `[^`]+`", instructions, re.M)
            or (repo / ".devcontainer").exists()
        ),
        "lockfiles": all(
            any((m.parent / lock).exists() or (repo / lock).exists() for lock in LOCKS[m.name])
            for m in _manifests(repo)
        ),
        "typed": _typed(repo),
        "ci": any((repo / ".github" / "workflows").glob("*.y*ml")),
    }
    return checks


def _typed(repo: Path) -> bool:
    if any(_manifests_named(repo, "Cargo.toml")):
        return True
    ts = repo / "tsconfig.json"
    if ts.exists() and json.loads(_text(ts)).get("compilerOptions", {}).get("strict"):
        return True
    return "[tool.mypy]" in "".join(_text(p) for p in _manifests_named(repo, "pyproject.toml"))


def _manifests_named(repo: Path, name: str) -> list[Path]:
    return [p for p in _manifests(repo) if p.name == name]


def score(checks: dict[str, bool]) -> str:
    return f"{sum(checks.values())}/{len(checks)}"
