"""browser_use_notes: explicit llm, the run judge as an eval row, and the toy cache-cost model."""

import json
from pathlib import Path

import browser_use_notes as bn
import pytest

J = json.loads((Path(__file__).parent / "fixtures" / "browser_use_judgements.json").read_text())[
    "judgements"
]


def test_no_llm_is_refused_unless_you_opt_into_the_default():
    with pytest.raises(ValueError, match="15x"):
        bn.explicit_llm(None)
    assert bn.explicit_llm(None, allow_default=True) == "bu-4.0"
    assert bn.explicit_llm("bu-fast") == "bu-fast"


def test_bu_4_0_tokens_cost_15x_bu_fast():
    assert bn.token_cost("bu-4.0", 10**6, 0) == pytest.approx(
        15 * bn.token_cost("bu-fast", 10**6, 0)
    )
    assert bn.token_cost("bu-4.0", 0, 10**6) == pytest.approx(
        15 * bn.token_cost("bu-fast", 0, 10**6)
    )
    # cached input is billed at the cached price
    assert bn.token_cost("bu-fast", 10**6, 0, cached_tokens=10**6) == pytest.approx(0.012)


@pytest.mark.parametrize(
    ("name", "checker", "passed", "label"),
    [
        ("clean_success", None, True, "pass"),
        ("success_with_gotcha", True, True, "pass"),
        ("captcha_block", None, False, "environment_blocked"),
        ("injection", True, False, "safety_review"),
        ("judged_failure", None, False, "agent_failure"),
        ("clean_success", False, False, "agent_failure"),  # the checker wins over the judge
    ],
)
def test_judgement_to_eval(name, checker, passed, label):
    row = bn.judgement_to_eval(name, J[name], checker)
    assert (row.passed, row.label) == (passed, label)


def test_gotchas_become_lessons_and_disagreement_is_recorded():
    row = bn.judgement_to_eval("t", J["success_with_gotcha"], checker_passed=True)
    assert row.lessons == ["The form requires phone numbers in (###) ###-#### format"]
    assert row.judge_agrees_with_checker is True
    assert bn.judgement_to_eval("t", J["clean_success"], False).judge_agrees_with_checker is False


def test_missing_judgement_falls_back_to_the_checker_and_bad_shapes_fail():
    assert bn.judgement_to_eval("t", None, checker_passed=True).label == "pass"
    assert bn.judgement_to_eval("t", None).label == "agent_failure"
    with pytest.raises(KeyError, match="gotchas"):
        bn.judgement_to_eval("t", {k: v for k, v in J["clean_success"].items() if k != "gotchas"})


def test_batch_pruning_sends_more_tokens_but_costs_less():
    every = bn.prompt_cost(100, policy="every")
    batch = bn.prompt_cost(100, policy="batch")
    assert batch["input_tokens"] > every["input_tokens"]  # images stay longer
    assert batch["cached_tokens"] > 0.9 * batch["input_tokens"]
    assert every["cached_tokens"] < 0.01 * every["input_tokens"]
    assert batch["usd"] < every["usd"] / 2


def test_short_runs_never_prune_so_both_policies_cost_the_same_until_keep():
    a = bn.prompt_cost(bn.KEEP_IMAGE_RESULTS, policy="every")
    b = bn.prompt_cost(bn.KEEP_IMAGE_RESULTS, policy="batch")
    assert a == b
    with pytest.raises(ValueError):
        bn.prompt_cost(3, policy="never")
