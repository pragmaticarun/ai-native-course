"""L15.2: what browser-use 1.0.4-1.0.6 changed, as a cost lesson and an eval lesson.

No browser-use import here: the facts are copied from the release notes and the docs' model
card, and `test_browser_use_pins.py` checks them against the real browser-use 1.0.6 package
(CI installs it in an isolated environment; its exact pins conflict with the course lock).

* 1.0.6: `Agent(task)` with no `llm` now runs `bu-4.0`, about 15x the token price of the old
  default `bu-fast`. So always pass `llm=` yourself (`explicit_llm`).
* 1.0.5: every run is judged by your own model and fills `result.judgement`
  (`judgement_to_eval` turns that into an eval row).
* 1.0.4: old screenshots are dropped in one batch once 20 tool results carry one, instead of
  on every new screenshot, so the provider's prompt cache keeps working (`prompt_cost`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

DEFAULT_LLM_1_0_6 = "bu-4.0"  # browser_use.llm.DEFAULT_MODEL in 1.0.6 ("bu-fast" before)
PRUNE_IMAGES_AT = 20  # browser_use.agent.loop, 1.0.4+: prune once this many results carry images
KEEP_IMAGE_RESULTS = 2  # ... then keep images only in the newest 2

# USD per 1M tokens: (input, cached input, output), from the gateway model card
# (https://docs.browser-use.com/open-source/models, read 17 Nov 2026). Cache-write prices exist
# too; the toy cost model below leaves them out.
PRICES: dict[str, tuple[float, float, float]] = {
    "bu-4.0": (1.80, 0.09, 9.00),
    "bu-4.0-mini": (0.20, 0.02, 1.00),
    "bu-fast": (0.12, 0.012, 0.60),
}

# The six Judgement fields browser-use 1.0.6 defines (browser_use.agent.judge.Judgement).
JUDGEMENT_FIELDS = (
    "success",
    "failure_reason",
    "description",
    "prompt_injection_detected",
    "bot_block_or_captcha_detected",
    "gotchas",
)


# ------------------------------------------------ 1.0.6: never rely on the default
def explicit_llm(llm: object, *, allow_default: bool = False) -> object:
    """Return `llm`, refusing None: a library default can change (and re-price) under you."""
    if llm is None or llm == "":
        if allow_default:
            return DEFAULT_LLM_1_0_6
        raise ValueError(
            "pass llm= explicitly: with no llm, browser-use 1.0.6 runs bu-4.0, "
            "about 15x the token price of bu-fast (the default before 1.0.6)"
        )
    return llm


def token_cost(model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float:
    """USD for one run's tokens; `cached_tokens` is the part of `input_tokens` read from cache."""
    price_in, price_cached, price_out = PRICES[model]
    fresh = input_tokens - cached_tokens
    return (fresh * price_in + cached_tokens * price_cached + output_tokens * price_out) / 1e6


# ------------------------------------------------ 1.0.5: the run judge as an eval signal
@dataclass
class EvalRow:
    task_id: str
    passed: bool
    label: str  # pass | agent_failure | environment_blocked | safety_review
    reason: str
    lessons: list[str] = field(default_factory=list)
    judge_agrees_with_checker: bool | None = None


def judgement_to_eval(
    task_id: str, judgement: Mapping[str, Any] | None, checker_passed: bool | None = None
) -> EvalRow:
    """Turn `result.judgement.model_dump()` into an eval row.

    The judge is a model grading its own run, so treat it as one signal: a deterministic checker
    (`checker_passed`, e.g. M15's state-based success check) wins when both exist. A CAPTCHA or
    bot block is an environment problem, not a policy failure; a detected prompt injection goes
    to a human whatever the verdict. Gotchas become lessons for the next run (M4 memory).
    """
    if judgement is None:  # judge=False, or the judge call failed: result.judgement is None
        passed = bool(checker_passed)
        return EvalRow(task_id, passed, "pass" if passed else "agent_failure", "no judgement")
    missing = [f for f in JUDGEMENT_FIELDS if f not in judgement]
    if missing:
        raise KeyError(f"not a browser-use Judgement, missing {missing}")
    judged_ok = bool(judgement["success"])
    passed = judged_ok if checker_passed is None else checker_passed
    if judgement["prompt_injection_detected"]:
        label, passed = "safety_review", False
    elif judgement["bot_block_or_captcha_detected"] and not passed:
        label = "environment_blocked"
    else:
        label = "pass" if passed else "agent_failure"
    reason = judgement["failure_reason"] or judgement["description"]
    agrees = None if checker_passed is None else judged_ok == checker_passed
    return EvalRow(task_id, passed, label, reason, list(judgement["gotchas"]), agrees)


# ------------------------------------------------ 1.0.4: keep the prompt cache warm
def prompt_cost(
    steps: int,
    *,
    policy: str,
    model: str = "bu-fast",
    text_tokens: int = 400,
    image_tokens: int = 1_500,
    output_tokens: int = 150,
    prune_at: int = PRUNE_IMAGES_AT,
    keep: int = KEEP_IMAGE_RESULTS,
) -> dict[str, float]:
    """A toy model of screenshot pruning vs prompt caching (not browser-use's real accounting).

    Every step appends one tool result with a screenshot and sends the whole conversation.
    Assumption: the cache entry is the previous request, written at a breakpoint on its last
    message, and it's read only if that request is still an unchanged prefix of the new one
    (providers differ: some look back a few blocks for an older entry, some cache any matching
    prefix). `policy="every"` strips old images on every new screenshot, rewriting an earlier
    message each time; `policy="batch"` lets images pile up to `prune_at`, then strips all but
    the newest `keep` at once, so only those steps miss the cache.
    """
    if policy not in ("every", "batch"):
        raise ValueError("policy is 'every' or 'batch'")
    msgs: list[list[int]] = []  # [text_tokens, image_tokens] per tool result
    prev: list[tuple[int, int]] = []
    sent = cached = 0
    for _ in range(steps):
        msgs.append([text_tokens, image_tokens])
        with_images = [m for m in msgs if m[1]]
        if (policy == "every" and len(with_images) > keep) or (
            policy == "batch" and len(with_images) > prune_at
        ):
            for m in with_images[:-keep]:
                m[1] = 0
        now = [(t, i) for t, i in msgs]
        if prev and now[: len(prev)] == prev:  # nothing earlier was rewritten: cache hit
            cached += sum(t + i for t, i in prev)
        sent += sum(t + i for t, i in now)
        prev = now
    usd = token_cost(model, sent, output_tokens * steps, cached)
    return {"input_tokens": sent, "cached_tokens": cached, "usd": round(usd, 4)}


if __name__ == "__main__":
    for p in ("every", "batch"):
        print(p, prompt_cost(100, policy=p))
    print("bu-4.0 vs bu-fast, 1M in + 100k out:", token_cost("bu-4.0", 10**6, 10**5),
          token_cost("bu-fast", 10**6, 10**5))  # fmt: skip
