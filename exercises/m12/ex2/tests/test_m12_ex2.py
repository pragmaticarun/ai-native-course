import math
import re

import dora
import yaml
from _impl import variant_dir

KIND = {
    "change_lead_time_h": "throughput",
    "deployment_frequency_per_week": "throughput",
    "failed_deployment_recovery_time_h": "throughput",
    "change_fail_rate": "instability",
    "deployment_rework_rate": "instability",
    "review_latency_h": "flow",
}
VANITY = re.compile(
    r"lines|loc\b|prompt|suggestion|accepted|ai_percent|percent_ai|written_by_ai|prs?_merged", re.I
)

PANELS = yaml.safe_load((variant_dir(__file__) / "dashboard.yaml").read_text())["panels"]
DEPS, PRS = dora.fictional_team(
    seed=12, weeks=8, per_week=5, fail_p=0.12, rework_p=0.06, review_h=4
)
ACTUAL = dora.metrics(DEPS, PRS, weeks=8)


def test_known_metrics_and_kinds():
    assert set(KIND) == set(ACTUAL)
    for p in PANELS:
        assert not VANITY.search(p["metric"]), f"vanity metric: {p['metric']}"
        assert p["metric"] in KIND, f"not computable from delivery data: {p['metric']}"
        assert p["kind"] == KIND[p["metric"]], p["metric"]


def test_balance_and_guards():
    names = {p["metric"] for p in PANELS}
    assert {"throughput", "instability"} <= {p["kind"] for p in PANELS}
    assert "review_latency_h" in names
    for p in PANELS:
        if p["kind"] == "throughput":
            g = p.get("guarded_by")
            assert g in names and KIND[g] in {"instability", "flow"}, (
                f"{p['metric']} needs a guard on the dashboard"
            )


def test_baselines_match_data():
    for p in PANELS:
        assert "baseline" in p, p["metric"]
        assert math.isclose(p["baseline"], ACTUAL[p["metric"]], rel_tol=0.01, abs_tol=1e-9), p[
            "metric"
        ]
