import ladder
from _impl import load

impl = load(__file__)
BASE = {"clear and communicated AI stance", "ai-policy", "strong version control practices"}
L2_ADDS = ["working in small batches", "agents-md", "fast-tests"]
L3_ADDS = [
    "AI-accessible internal data",
    "quality internal platforms",
    "pr-policy",
    "eval-suite",
    "verify-command",
]


def team(level=1, extra=()):
    have = BASE | set(extra)
    caps = {h for h in have if h in ladder.DORA_AI_CAPABILITIES}
    return ladder.Team("t", level, capabilities=caps, artifacts=have - caps)


def test_coherent_plan():
    plan = {
        "stages": [
            {"target": 2, "adds": L2_ADDS, "agent_prs_per_week": 4, "reviewer_hours_per_week": 10},
            {"target": 3, "adds": L3_ADDS, "agent_prs_per_week": 12, "reviewer_hours_per_week": 10},
        ]
    }
    assert impl.critique(plan, team()) == []


def test_big_bang_plan():
    plan = {
        "stages": [
            {
                "target": 3,
                "adds": ["agents-md"],
                "agent_prs_per_week": 40,
                "reviewer_hours_per_week": 10,
            }
        ]
    }
    assert impl.critique(plan, team()) == [
        "stage 1: skips from L1 to L3",
        "stage 1: missing working in small batches",
        "stage 1: missing fast-tests",
        "stage 1: missing AI-accessible internal data",
        "stage 1: missing quality internal platforms",
        "stage 1: missing pr-policy",
        "stage 1: missing eval-suite",
        "stage 1: missing verify-command",
        "stage 1: review load 2.0",
    ]


def test_dark_factory_and_prereqs_from_earlier_stages():
    plan = {
        "stages": [
            {"target": 3, "adds": L3_ADDS, "agent_prs_per_week": 10, "reviewer_hours_per_week": 8},
            {
                "target": 4,
                "adds": ["specs", "skills", "sandbox", "agent-budgets", "user-centric focus"],
                "agent_prs_per_week": 10,
                "reviewer_hours_per_week": 6,
            },
            {"target": 5, "adds": [], "agent_prs_per_week": 10, "reviewer_hours_per_week": 8},
        ]
    }
    assert impl.critique(plan, team(2, L2_ADDS)) == [
        "stage 2: missing healthy data ecosystems",
        "stage 2: review load 0.83",
        "stage 3: targets L5",
    ]
