"""M11 L11.5: check a headless-agent workflow for the guardrails this course asks for.

Rules (ours): read-only default permissions; every job has a timeout; a job that uses a
secret can't also have write permissions; checkout in that job doesn't persist the
token; the agent job is behind a kill-switch variable; runs are serialised per issue;
PRs are opened as drafts with a provenance label.
"""

from __future__ import annotations

import re
from typing import Any

import yaml


def lint_workflow(text: str) -> list[str]:
    wf: dict[Any, Any] = yaml.safe_load(text)
    problems = []
    if wf.get("permissions") not in ({"contents": "read"}, "read-all", {}):
        problems.append("top-level permissions must be read-only")
    if "concurrency" not in wf:
        problems.append("no concurrency group: two runs could race on one issue")
    for name, job in wf.get("jobs", {}).items():
        body = yaml.safe_dump(job)
        writes = any(v == "write" for v in (job.get("permissions") or {}).values())
        if "timeout-minutes" not in job:
            problems.append(f"{name}: no timeout-minutes")
        if "secrets." in body and writes:
            problems.append(f"{name}: holds a secret and has write permissions")
        if "secrets." in body:
            for step in job.get("steps", []):
                if (
                    str(step.get("uses", "")).startswith("actions/checkout")
                    and (step.get("with") or {}).get("persist-credentials") is not False
                ):
                    problems.append(f"{name}: checkout persists the token next to the agent")
            if not re.search(r"vars\.AGENT_PIPELINE_ENABLED == 'true'", str(job.get("if", ""))):
                problems.append(f"{name}: no kill switch on the agent job")
        if "gh pr create" in body and not ("--draft" in body and "agent-authored" in body):
            problems.append(f"{name}: PRs must be drafts labelled agent-authored")
    return problems
