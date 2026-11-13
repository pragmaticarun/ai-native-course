"""M12 L12.4: a 90-day adoption plan as data, with structural checks.

Template (this course's): up to four stages; each names the target level, the metrics
it watches with a baseline and a target, at least one guardrail metric (what must not
get worse), an exit criterion and an owner. Vanity metrics are refused (Thoughtworks
Radar Vol. 35 also cautions against coding throughput as a productivity measure).
"""

from __future__ import annotations

from datetime import date
from typing import Any

import yaml

VANITY = (
    "lines of code",
    "% of code written by ai",
    "number of prompts",
    "ai suggestions accepted",
    "prs merged",
)


def load(text: str) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(text)
    return data


def check_plan(plan: dict[str, Any]) -> list[str]:
    problems = []
    stages = plan.get("stages", [])
    start = date.fromisoformat(str(plan["start"]))
    if not 1 <= len(stages) <= 4:
        problems.append("use 1-4 stages")
    for i, s in enumerate(stages, 1):
        tag = f"stage {i} ({s.get('name', '?')})"
        if not s.get("exit_criterion"):
            problems.append(f"{tag}: no exit criterion")
        if not s.get("owner"):
            problems.append(f"{tag}: no owner")
        metrics = s.get("metrics", [])
        if not any(m.get("guardrail") for m in metrics):
            problems.append(f"{tag}: no guardrail metric")
        for m in metrics:
            if m["name"].lower() in VANITY:
                problems.append(f"{tag}: vanity metric '{m['name']}'")
            if "baseline" not in m or "target" not in m:
                problems.append(f"{tag}: metric '{m['name']}' needs a baseline and a target")
    end = date.fromisoformat(str(stages[-1]["ends"])) if stages else start
    if (end - start).days > 90:
        problems.append(f"plan runs {(end - start).days} days (> 90)")
    return problems
