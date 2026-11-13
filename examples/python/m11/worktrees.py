"""M11 L11.3: parallel agents in git worktrees, planned so their branches don't conflict.

`plan_batches` puts tasks in the same batch only if their file sets are disjoint
(greedy colouring; tasks keep their order). Each batch runs in parallel, one worktree
and branch per task, then merges into main before the next batch branches off.
`git worktree` gives every agent its own checkout of the same repository.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from subprocess import CalledProcessError

from sandbox import git

Edits = dict[str, Callable[[str], str]]  # path -> edit(old content) -> new content


def plan_batches(tasks: dict[str, set[str]]) -> list[list[str]]:
    batches: list[tuple[list[str], set[str]]] = []
    for name, files in tasks.items():
        for names, used in batches:
            if not used & files:
                names.append(name)
                used |= files
                break
        else:
            batches.append(([name], set(files)))
    return [names for names, _ in batches]


def add_worktree(repo: Path, name: str) -> Path:
    wt = repo.parent / f"wt-{name}"
    git(repo, "worktree", "add", "-q", "-b", f"agent/{name}", str(wt), "main")
    return wt


def agent_work(wt: Path, name: str, edits: Edits) -> None:
    """What one agent does in its own checkout (here: scripted edits, then a commit)."""
    for path, edit in edits.items():
        f = wt / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(edit(f.read_text() if f.exists() else ""))
    git(wt, "add", ".")
    git(wt, "commit", "-qm", f"{name} (agent)")


def merge(repo: Path, branches: list[str]) -> list[str]:
    conflicts = []
    for b in branches:
        try:
            git(repo, "merge", "-q", "--no-edit", b)
        except CalledProcessError:
            git(repo, "merge", "--abort")
            conflicts.append(b)
    return conflicts


def run_parallel(repo: Path, batches: list[list[str]], edits: dict[str, Edits]) -> list[str]:
    conflicts: list[str] = []
    for batch in batches:
        # Creating and removing worktrees touches shared repo metadata: do it serially.
        trees = {n: add_worktree(repo, n) for n in batch}
        with ThreadPoolExecutor(max_workers=len(batch)) as pool:  # the agents run in parallel
            list(pool.map(agent_work, [trees[n] for n in batch], batch, [edits[n] for n in batch]))
        for wt in trees.values():
            git(repo, "worktree", "remove", str(wt))
        conflicts += merge(repo, [f"agent/{n}" for n in batch])
    return conflicts
