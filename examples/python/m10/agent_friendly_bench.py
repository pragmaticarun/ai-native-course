"""M10 worked example: measure a (mock) agent on a Rust crate before and after making
the repo agent-friendly.

The crate (fixtures/rustlib) hides one trap many real repos have: its integration tests
only compile with `--features full`, so plain `cargo test` is green with zero of them run.
The "after" overlay adds AGENTS.md (with a `Verify:` line) and verify.sh.

The agent is a deterministic stand-in, not a model:
* it runs only the verify command the repo documents in AGENTS.md (`Verify: `...``);
  with none, it guesses `cargo test`, as a newcomer would;
* for each task it tries candidate patches in order and keeps the first one that
  verifies.
Success is judged by the ground truth (`cargo test --features full`).

The numbers it prints are a property of this mock and these fixtures. They show *how*
to measure; they are not evidence about any real agent. Point `Agent` at a live
coding agent to measure your own repo (not done in this course: untested).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).parent / "fixtures"
GROUND_TRUTH = ["cargo", "test", "--quiet", "--offline", "--features", "full"]

REFERENCE = {
    "to_frames": "((tc.h as u64 * 60 + tc.m as u64) * 60 + tc.s as u64) * fps as u64 + tc.f as u64",
    "from_frames": (
        "let fps = fps as u64;\n    let (f, secs) = (frames % fps, frames / fps);\n"
        "    Timecode { h: (secs / 3600) as u32, m: (secs / 60 % 60) as u32, s: (secs % 60) as u32, f: f as u32 }"  # noqa: E501
    ),
    "parse": (
        "let p: Vec<u32> = text.split(':').map(|x| x.parse().map_err(|_| text.to_string())).collect::<Result<_, _>>()?;\n"  # noqa: E501
        '    if p.len() != 4 || p[1] > 59 || p[2] > 59 {\n        return Err(format!("bad timecode {text}"));\n    }\n'  # noqa: E501
        "    Ok(Timecode { h: p[0], m: p[1], s: p[2], f: p[3] })"
    ),
    "format": 'format!("{:02}:{:02}:{:02}:{:02}", tc.h, tc.m, tc.s, tc.f)',
    "between": "to_frames(b, fps).checked_sub(to_frames(a, fps))",
}

# Five seeded tasks. Each lists the patches the "agent" would try, in order.
TASKS: dict[str, list[str]] = {
    "to_frames": [REFERENCE["to_frames"]],
    "from_frames": [
        "let fps = fps as u64;\n    let secs = frames / fps;\n"
        "    Timecode { h: (secs / 3600) as u32, m: (secs / 60) as u32, s: (secs % 60) as u32, f: (frames % fps) as u32 }",  # noqa: E501
        REFERENCE["from_frames"],
    ],
    "parse": [
        "let p: Vec<u32> = text.split(':').map(|x| x.parse().unwrap_or(0)).collect();\n"
        "    Ok(Timecode { h: p[0], m: p[1], s: p[2], f: *p.get(3).unwrap_or(&0) })",
        REFERENCE["parse"],
    ],
    "format": ['format!("{}:{}:{}:{}", tc.h, tc.m, tc.s, tc.f)', REFERENCE["format"]],
    "between": [REFERENCE["between"]],
}


def write_lib(repo: Path, task: str, patch: str) -> None:
    src = (HERE / "rustlib" / "src" / "lib.rs.tmpl").read_text()
    for name, body in REFERENCE.items():
        src = src.replace(f"    // TASK:{name}", "    " + (patch if name == task else body))
    (repo / "src" / "lib.rs").write_text(src)


def make_repo(dest: Path, friendly: bool) -> Path:
    shutil.copytree(HERE / "rustlib", dest, ignore=shutil.ignore_patterns("target"))
    if friendly:
        shutil.copytree(HERE / "rustlib_after", dest, dirs_exist_ok=True)
    return dest


def documented_verify(repo: Path) -> list[str] | None:
    agents = repo / "AGENTS.md"
    if agents.exists():
        m = re.search(r"^Verify: `([^`]+)`", agents.read_text(), re.M)
        if m:
            return m.group(1).split()
    return None


def run(cmd: list[str], repo: Path, target: Path) -> bool:
    env = {**os.environ, "CARGO_TARGET_DIR": str(target), "CARGO_NET_OFFLINE": "true"}
    return subprocess.run(cmd, cwd=repo, env=env, capture_output=True).returncode == 0


@dataclass
class Result:
    friendly: bool
    verify_cmd: list[str]
    solved: dict[str, bool] = field(default_factory=dict)
    verify_runs: int = 0

    @property
    def success_rate(self) -> float:
        return sum(self.solved.values()) / len(self.solved)


def bench(workdir: Path, friendly: bool) -> Result:
    repo = make_repo(workdir / ("after" if friendly else "before"), friendly)
    target = workdir / "target"
    verify = documented_verify(repo) or ["cargo", "test", "--quiet", "--offline"]
    res = Result(friendly, verify)
    for task, candidates in TASKS.items():
        chosen = candidates[0]
        for patch in candidates:
            write_lib(repo, task, patch)
            res.verify_runs += 1
            if run(verify, repo, target):
                chosen = patch
                break
        write_lib(repo, task, chosen)
        res.solved[task] = run(GROUND_TRUTH, repo, target)
    return res


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        for friendly in (False, True):
            r = bench(Path(d), friendly)
            print(
                f"friendly={friendly} verify={' '.join(r.verify_cmd)!r} "
                f"success={r.success_rate:.0%} verify_runs={r.verify_runs} {r.solved}"
            )
