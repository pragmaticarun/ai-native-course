"""M12 L12.3: supply-chain checks for agent-added dependencies.

Motivating incident (17 Nov 2026): Microsoft's `agent-framework` 1.26.1 and 1.26.2 on PyPI
each dropped a `.pth` file into site-packages (`agent_framework_meta.pth`,
`af_runtime_diag.pth`). Python runs `import` lines in `.pth` files on every interpreter
start, so the credential stealer ran whenever Python started in that environment, pip
included, without anything importing the package. Both versions were quarantined within
hours. Sources: The Register and The Hacker News, 18 Nov 2026 (links on the lesson page).

Four checks, all offline and deterministic:

1. `audit_requirements`: every requirement is an exact `==` pin with at least one
   `--hash=sha256:` (what `pip install --require-hashes` enforces).
2. `scan_startup_hooks`: list the files in a site-packages directory that run code at
   interpreter start: `.pth` lines starting with `import` (deprecated in Python 3.15 but
   still executed) and Python 3.15 `.start` entry points.
3. `cooldown_violations`: which pinned releases are younger than a minimum release age
   (pnpm `minimumReleaseAge`, uv `exclude-newer = "1 day"`).
4. `workflow_token_findings`: GitHub Actions permissions that let any step mint a cloud
   token (`id-token: write`) or write to the repo.

The rule set is this course's; it is not a published standard.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Indicators of compromise from the agent-framework incident (The Hacker News, 18 Nov 2026).
KNOWN_BAD_STARTUP_FILES = frozenset({"agent_framework_meta.pth", "af_runtime_diag.pth"})
KNOWN_BAD_RELEASES = frozenset({("agent-framework", "1.26.1"), ("agent-framework", "1.26.2")})

_REQ = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*(?P<spec>[^;\s]*)")


@dataclass(frozen=True)
class Finding:
    where: str
    problem: str

    def __str__(self) -> str:
        return f"{self.where}: {self.problem}"


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _logical_lines(text: str) -> list[str]:
    """Join backslash continuations (how `pip-compile --generate-hashes` writes hashes)."""
    out: list[str] = []
    buf = ""
    for raw in text.splitlines():
        line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if line.endswith("\\"):
            buf += line[:-1] + " "
            continue
        buf += line
        if buf.strip():
            out.append(buf.strip())
        buf = ""
    return out


def audit_requirements(text: str) -> list[Finding]:
    """Flag requirements that are not exact pins, carry no hash, or are known-bad releases."""
    findings: list[Finding] = []
    for line in _logical_lines(text):
        if line.startswith("-"):  # options such as --index-url; mirrors are reviewed elsewhere
            continue
        m = _REQ.match(line)
        if not m:
            findings.append(Finding(line, "unparseable requirement"))
            continue
        name, spec = _norm(m["name"]), m["spec"]
        version = spec[2:] if spec.startswith("==") else ""
        if not version or any(c in version for c in "*,<>~!="):
            findings.append(Finding(name, f"not an exact pin ({spec or 'no version'})"))
        elif (name, version) in KNOWN_BAD_RELEASES:
            findings.append(Finding(name, f"known-compromised release {version}"))
        if "--hash=sha256:" not in line:
            findings.append(Finding(name, "no --hash=sha256 (install with --require-hashes)"))
    return findings


def _executable_lines(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if path.suffix == ".start":  # every non-comment line is a pkg.mod:callable entry point
        return [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    return [ln for ln in lines if ln.startswith(("import ", "import\t"))]


def scan_startup_hooks(site_packages: Path, allow: frozenset[str] = frozenset()) -> list[Finding]:
    """Startup hooks in one site-packages directory. Path-only `.pth` lines are fine."""
    findings: list[Finding] = []
    for p in sorted([*site_packages.glob("*.pth"), *site_packages.glob("*.start")]):
        if p.name in KNOWN_BAD_STARTUP_FILES:
            findings.append(Finding(p.name, "known indicator of compromise (agent-framework)"))
            continue
        code = _executable_lines(p)
        if code and p.name not in allow:
            findings.append(Finding(p.name, f"runs at every Python start: {code[0][:60]!r}"))
    return findings


def cooldown_violations(
    pins: dict[str, str],
    uploaded: dict[tuple[str, str], datetime],
    now: datetime,
    min_age: timedelta = timedelta(days=1),
) -> list[Finding]:
    """Pinned releases younger than `min_age` (the pnpm and uv cooldown idea)."""
    findings = []
    for name, version in sorted(pins.items()):
        when = uploaded.get((_norm(name), version))
        if when is None:
            findings.append(Finding(f"{name}=={version}", "upload time unknown: not on the index?"))
        elif now - when < min_age:
            hours = (now - when).total_seconds() / 3600
            findings.append(Finding(f"{name}=={version}", f"only {hours:.1f} h old"))
    return findings


# Actions that may share a job with `id-token: write`: they install nothing from a registry.
TOKEN_JOB_ACTIONS = frozenset(
    {
        "actions/checkout",
        "actions/download-artifact",
        "actions/deploy-pages",
        "actions/configure-pages",
    }
)
_INSTALL = re.compile(
    r"\b(pip install|uv (sync|add|pip install)|pnpm (install|add)|npm (i|install|ci))\b"
)


def workflow_token_findings(workflow: dict[str, Any]) -> list[Finding]:
    """GitHub Actions: read-only by default; `id-token: write` only on jobs that install nothing.

    A job's effective permissions are its own `permissions:` or, if it has none, the
    workflow's. Any job that can mint an OIDC token must not install packages or run
    actions that do (a build action installs the whole dependency tree).
    """
    findings: list[Finding] = []
    top = workflow.get("permissions")
    if top is None:
        findings.append(Finding("workflow", "no top-level permissions: GITHUB_TOKEN gets defaults"))
    elif top == "write-all" or (isinstance(top, dict) and "write" in top.values()):
        findings.append(Finding("workflow", f"top-level write permissions {top!r}"))
    for job_id, job in (workflow.get("jobs") or {}).items():
        perms = job.get("permissions", top) or {}
        if not (
            perms == "write-all" or (isinstance(perms, dict) and perms.get("id-token") == "write")
        ):
            continue
        for step in job.get("steps") or []:
            uses = str(step.get("uses", "")).split("@", 1)[0]
            run = str(step.get("run", ""))
            if (uses and uses not in TOKEN_JOB_ACTIONS) or _INSTALL.search(run):
                what = uses or run.splitlines()[0][:50]
                findings.append(
                    Finding(f"jobs.{job_id}", f"can mint OIDC tokens and runs {what!r}")
                )
                break
    return findings
