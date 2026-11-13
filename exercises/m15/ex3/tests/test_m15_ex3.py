import json
from pathlib import Path

import pytest
from _impl import load

impl = load(__file__)
EPS = json.loads((Path(__file__).parent / "episodes.json").read_text())["episodes"]


@pytest.mark.parametrize("ep", EPS, ids=[f"{e['task']}-{e['agent']}" for e in EPS])
def test_checker_reads_state_not_claims(ep):
    assert impl.check(ep["task"], ep["params"], ep["claim"], ep["state"]) is ep["expected"]


def test_pass_at_1_per_agent():
    for agent, want in (("A", 1.0), ("B", 0.0)):
        res = [
            impl.check(e["task"], e["params"], e["claim"], e["state"])
            for e in EPS
            if e["agent"] == agent
        ]
        assert impl.pass_at_1(res) == want
    assert impl.pass_at_1([]) == 0.0
