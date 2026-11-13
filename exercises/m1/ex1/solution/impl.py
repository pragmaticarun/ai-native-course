SHAPIRO = [  # (fact, level), lowest to highest
    ("delegates_discrete_tasks", 1),
    ("pairs_in_flow", 2),
    ("reviews_agent_diffs_mostly", 3),
    ("writes_specs_and_leaves", 4),
    ("no_human_code_review", 5),
]
FENG = [
    ("user_drives_every_step", "L1"),
    ("user_and_agent_share_work", "L2"),
    ("agent_leads_user_advises", "L3"),
    ("user_only_approves_key_actions", "L4"),
    ("user_only_monitors", "L5"),
]


def place(team: dict[str, bool]) -> dict[str, object]:
    shapiro = 0
    if team.get("uses_ai", True):
        shapiro = max([lvl for fact, lvl in SHAPIRO if team.get(fact)], default=0)
    feng = max([lvl for fact, lvl in FENG if team.get(fact)], default="L1")
    # The placements can differ because the models measure different things:
    # Shapiro rates the whole engineering workflow, Feng et al. rate the user's
    # role towards one agent. A team can review most code as agent diffs
    # (Shapiro L3) while every individual agent session is collaborative (Feng L2).
    return {"shapiro": shapiro, "feng": feng}
