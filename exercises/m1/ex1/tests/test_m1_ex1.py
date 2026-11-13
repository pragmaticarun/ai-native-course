from _impl import load

impl = load(__file__)


def test_team_a_no_ai():
    assert impl.place({"uses_ai": False, "user_drives_every_step": True}) == {
        "shapiro": 0,
        "feng": "L1",
    }


def test_team_b_reviews_diffs_but_collaborates():
    team = {
        "uses_ai": True,
        "pairs_in_flow": True,
        "reviews_agent_diffs_mostly": True,
        "user_and_agent_share_work": True,
    }
    assert impl.place(team) == {"shapiro": 3, "feng": "L2"}


def test_team_c_spec_driven_approver():
    team = {
        "uses_ai": True,
        "delegates_discrete_tasks": True,
        "writes_specs_and_leaves": True,
        "user_and_agent_share_work": True,
        "user_only_approves_key_actions": True,
    }
    assert impl.place(team) == {"shapiro": 4, "feng": "L4"}
