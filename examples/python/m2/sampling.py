"""L2.1: an LLM is a stochastic function. Temperature and top-p, on toy logits.

Real models produce logits over ~100k-200k tokens; here we use five so you can
see the numbers. Same seed -> same sample; different seed -> maybe different.
"""

from __future__ import annotations

import math
import random

TOY_LOGITS = {"cat": 2.0, "dog": 1.5, "car": 0.3, "cloud": -0.5, "C++": -1.0}


def softmax(logits: dict[str, float], temperature: float = 1.0) -> dict[str, float]:
    if temperature <= 0:  # greedy decoding: all mass on the argmax
        best = max(logits, key=logits.__getitem__)
        return {t: (1.0 if t == best else 0.0) for t in logits}
    scaled = {t: v / temperature for t, v in logits.items()}
    peak = max(scaled.values())
    exps = {t: math.exp(v - peak) for t, v in scaled.items()}
    total = sum(exps.values())
    return {t: e / total for t, e in exps.items()}


def top_p_filter(probs: dict[str, float], top_p: float) -> dict[str, float]:
    """Keep the smallest set of tokens whose probability sums to >= top_p."""
    kept: dict[str, float] = {}
    running = 0.0
    for token, p in sorted(probs.items(), key=lambda kv: kv[1], reverse=True):
        kept[token] = p
        running += p
        if running >= top_p:
            break
    total = sum(kept.values())
    return {t: p / total for t, p in kept.items()}


def sample(logits: dict[str, float], temperature: float, top_p: float, seed: int) -> str:
    probs = top_p_filter(softmax(logits, temperature), top_p)
    rng = random.Random(seed)
    return rng.choices(list(probs), weights=list(probs.values()), k=1)[0]


def approx_tokens(text: str) -> int:
    """Rule-of-thumb estimate (~4 characters per token for English). Not a real tokenizer."""
    return max(1, round(len(text) / 4))


if __name__ == "__main__":
    for t in (0.0, 0.7, 1.5):
        dist = softmax(TOY_LOGITS, t)
        print(f"T={t}: " + ", ".join(f"{k}={v:.2f}" for k, v in dist.items()))
    print("10 samples at T=1.0:", [sample(TOY_LOGITS, 1.0, 1.0, s) for s in range(10)])
