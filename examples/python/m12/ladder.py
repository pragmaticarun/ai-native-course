"""M12: the course's working ladder — Shapiro's levels for the engineering workflow,
with DORA's seven AI capabilities as entry criteria for moving up.

SOURCES
* Levels 0-5: Dan Shapiro, "The Five Levels: from Spicy Autocomplete to the Dark
  Factory" (blog post, 23 Jan 2026). One practitioner's opinion piece, not research.
* Capabilities: DORA AI Capabilities Model (2025), the seven capabilities that amplify
  AI's benefits.
* Review load: Thoughtworks Technology Radar Vol. 35 (Nov 2026) cautions against
  "human-in-the-loop theater" and says to assess review capacity before scaling agents.

THIS COURSE'S SYNTHESIS (not published by Shapiro, DORA or Thoughtworks): which
capabilities and team artifacts we ask for before each move up, and the 0.8
review-load threshold.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SHAPIRO = {
    0: "Manual: AI as a search engine or the odd tab-completion; every character is yours.",
    1: "Offload discrete tasks to an AI intern ('write a unit test'); your job is unchanged.",
    2: "Pair with an AI-native tool in flow; feels done, but isn't.",
    3: "You manage agents and review diffs all day; 'almost everyone tops out here'.",
    4: "You write specs and skills, review plans, leave, and check the tests passed.",
    5: "Dark factory: a black box that turns specs into software.",
}

DORA_AI_CAPABILITIES = (
    "clear and communicated AI stance",
    "healthy data ecosystems",
    "AI-accessible internal data",
    "strong version control practices",
    "working in small batches",
    "user-centric focus",
    "quality internal platforms",
)

# Course synthesis: what must be true *before* a team moves to the level.
ENTRY: dict[int, dict[str, tuple[str, ...]]] = {
    1: {"capabilities": ("clear and communicated AI stance",), "artifacts": ("ai-policy",)},
    2: {
        "capabilities": ("strong version control practices", "working in small batches"),
        "artifacts": ("agents-md", "fast-tests"),
    },
    3: {
        "capabilities": ("AI-accessible internal data", "quality internal platforms"),
        "artifacts": ("pr-policy", "eval-suite", "verify-command"),
    },
    4: {
        "capabilities": ("healthy data ecosystems", "user-centric focus"),
        "artifacts": ("specs", "skills", "sandbox", "agent-budgets"),
    },
}
NOT_A_TARGET = 5  # described, not planned for: too few verifiable cases to teach from
MAX_REVIEW_LOAD = 0.8


@dataclass
class Team:
    name: str
    level: int
    capabilities: set[str] = field(default_factory=set)
    artifacts: set[str] = field(default_factory=set)
    reviewer_hours_per_week: float = 0.0
    agent_prs_per_week: float = 0.0
    review_hours_per_pr: float = 0.5


def gaps(team: Team, target: int) -> list[str]:
    """Everything missing to move from team.level up to `target`, level by level."""
    out = []
    for lvl in range(team.level + 1, target + 1):
        if lvl >= NOT_A_TARGET:
            out.append(f"L{lvl}: not a target in this course")
            continue
        need = ENTRY[lvl]
        out += [
            f"L{lvl} capability: {c}" for c in need["capabilities"] if c not in team.capabilities
        ]
        out += [f"L{lvl} artifact: {a}" for a in need["artifacts"] if a not in team.artifacts]
    return out


def review_load(team: Team) -> float:
    """Fraction of reviewer time agent PRs would take. Near or above 1.0, review turns
    into rubber-stamping."""
    if team.reviewer_hours_per_week == 0:
        return float("inf") if team.agent_prs_per_week else 0.0
    return round(
        team.agent_prs_per_week * team.review_hours_per_pr / team.reviewer_hours_per_week, 2
    )


def ready_for(team: Team, target: int) -> tuple[bool, list[str]]:
    problems = gaps(team, target)
    if target >= 3 and review_load(team) > MAX_REVIEW_LOAD:
        problems.append(f"review load {review_load(team)} > {MAX_REVIEW_LOAD} of reviewer time")
    return (not problems, problems)
