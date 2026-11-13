from _impl import load
from assess import CAPABILITIES, Worksheet

impl = load(__file__)


def ws(level: int, **scores: int) -> Worksheet:
    caps = {c: 2 for c in CAPABILITIES} | scores
    return Worksheet(team="t", workflow_level=level, capabilities=caps)


def test_gaps_for_next_level_sorted_by_score_then_name():
    plan = impl.next_level_plan(ws(3, quality_internal_platforms=1, ai_accessible_internal_data=0))
    assert plan == [
        "Raise ai_accessible_internal_data from 0 to 2",
        "Raise quality_internal_platforms from 1 to 2",
    ]


def test_working_above_capabilities_stabilises_first():
    plan = impl.next_level_plan(ws(3, small_batches=1, strong_version_control=1))
    assert plan == [
        "Stabilise at L2: raise small_batches to 2",
        "Stabilise at L2: raise strong_version_control to 2",
    ]


def test_ready():
    assert impl.next_level_plan(ws(2)) == ["Ready for L3: run a two-week pilot and measure"]
