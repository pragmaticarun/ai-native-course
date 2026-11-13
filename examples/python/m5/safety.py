"""L5.6: safety boundaries. Least-privilege tools and dry-run mode.

* Each task gets only the tools it needs (`ToolRegistry.for_task`).
* Write tools declare themselves; in dry-run mode they describe what they
  WOULD do and change nothing. Run dry first, show the plan, then run for real.
* Paths are confined to a sandbox root.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ToolDef:
    name: str
    fn: Callable[..., str]
    writes: bool = False


@dataclass
class ToolRegistry:
    tools: dict[str, ToolDef] = field(default_factory=dict)

    def add(self, t: ToolDef) -> None:
        self.tools[t.name] = t

    def for_task(self, allowed: set[str], dry_run: bool) -> dict[str, Callable[..., str]]:
        out: dict[str, Callable[..., str]] = {}
        for name in sorted(allowed & self.tools.keys()):
            t = self.tools[name]
            if t.writes and dry_run:
                out[name] = lambda _n=name, **kw: f"DRY RUN: would call {_n}({kw})"
            else:
                out[name] = t.fn
        return out


def sandboxed(root: Path) -> Callable[[str], Path]:
    base = root.resolve()

    def resolve(rel: str) -> Path:
        p = (base / rel).resolve()
        if p != base and base not in p.parents:
            raise PermissionError(f"{rel} escapes the sandbox")
        return p

    return resolve


def file_tools(root: Path) -> ToolRegistry:
    safe = sandboxed(root)

    def read(path: str) -> str:
        return safe(path).read_text()

    def delete(path: str) -> str:
        safe(path).unlink()
        return f"deleted {path}"

    reg = ToolRegistry()
    reg.add(ToolDef("read", read))
    reg.add(ToolDef("delete", delete, writes=True))
    return reg
