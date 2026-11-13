"""M10 L10.6: guardrails in the dev loop — secret scanning, command allowlists, and a
sandboxed runner.

`allowed()` follows the rule shape Claude Code documents for `--allowedTools`
(e.g. `Bash(git diff *)`: the trailing ` *` makes it a prefix match, and the space
matters: `git diff*` would also match `git diff-index`). Deny rules win over allow
rules, as in Claude Code and Copilot CLI. The rest (splitting `&&`/`;`/`|` chains so a
safe prefix can't smuggle a second command, the env scrub) is this course's code.

`run_sandboxed` is *not* a security boundary: it limits time, working directory and
environment, nothing more. Real isolation needs a container/VM and an egress policy.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

SECRET_PATTERNS = {
    "aws-access-key-id": r"\bAKIA[0-9A-Z]{16}\b",
    "github-token": r"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,})\b",
    "private-key": r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----",
    "assigned-secret": r"(?i)\b(?:api|secret|token|passwd|password)[_-]?(?:key)?\s*[:=]\s*['\"][^'\"\s]{16,}['\"]",  # noqa: E501
}


def scan_secrets(text: str) -> list[tuple[int, str]]:
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if "secret-scan: allow" in line:  # explicit, reviewable escape hatch
            continue
        hits += [(lineno, name) for name, pat in SECRET_PATTERNS.items() if re.search(pat, line)]
    return hits


def _match(rule: str, command: str) -> bool:
    m = re.fullmatch(r"Bash\((.+)\)", rule)
    if not m:
        return False
    pat = m.group(1)
    if pat.endswith(" *"):
        prefix = pat[:-2]
        return command == prefix or command.startswith(prefix + " ")
    return command == pat


@dataclass
class CommandPolicy:
    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)

    def decide(self, command_line: str) -> tuple[bool, str]:
        parts = [p.strip() for p in re.split(r"&&|\|\||;|\||\n", command_line) if p.strip()]
        if re.search(r"\$\(|`", command_line):
            return False, "command substitution is never auto-approved"
        for part in parts:
            if any(_match(r, part) for r in self.deny):
                return False, f"denied: {part}"
            if not any(_match(r, part) for r in self.allow):
                return False, f"not on the allowlist: {part}"
        return True, "ok"


KEEP_ENV = ("PATH", "HOME", "LANG", "TERM", "CARGO_HOME", "RUSTUP_HOME", "UV_CACHE_DIR")


def run_sandboxed(
    command_line: str, cwd: Path, policy: CommandPolicy, timeout: float = 30
) -> subprocess.CompletedProcess[str]:
    ok, why = policy.decide(command_line)
    if not ok:
        raise PermissionError(why)
    env = {k: v for k, v in os.environ.items() if k in KEEP_ENV}  # no tokens, no keys
    return subprocess.run(
        shlex.split(command_line), cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout
    )
