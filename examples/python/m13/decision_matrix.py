"""M13 L13.1: on-device, cloud, or hybrid? A weighted decision matrix you can argue with.

Scores (0-3) are *our* teaching defaults, not measurements: change them for your app and
device. The point is to write the trade-off down and make hard constraints veto options.
"""

from __future__ import annotations

from dataclasses import dataclass

OPTIONS = ("on_device", "cloud", "hybrid")
# criterion -> how well each option does (0..3); defaults for a small phone-class model
DEFAULT_SCORES: dict[str, dict[str, int]] = {
    "latency": {"on_device": 3, "cloud": 1, "hybrid": 2},
    "privacy": {"on_device": 3, "cloud": 1, "hybrid": 2},
    "offline": {"on_device": 3, "cloud": 0, "hybrid": 2},
    "cost_per_call": {"on_device": 3, "cloud": 1, "hybrid": 2},
    "capability": {"on_device": 1, "cloud": 3, "hybrid": 3},
    "context_size": {"on_device": 1, "cloud": 3, "hybrid": 2},
    "battery": {"on_device": 1, "cloud": 2, "hybrid": 2},
    "storage_download": {"on_device": 0, "cloud": 3, "hybrid": 1},
    "fragmentation": {"on_device": 0, "cloud": 3, "hybrid": 2},
}


@dataclass(frozen=True)
class Requirements:
    weights: dict[str, float]
    must_work_offline: bool = False
    data_must_stay_on_device: bool = False
    needs_large_context: bool = False  # beyond what the on-device model accepts


def decide(
    req: Requirements, scores: dict[str, dict[str, int]] = DEFAULT_SCORES
) -> tuple[str, dict[str, float]]:
    vetoed = set()
    if req.must_work_offline:
        vetoed.add("cloud")
    if req.data_must_stay_on_device:
        vetoed |= {"cloud", "hybrid"}
    if req.needs_large_context:
        vetoed.add("on_device")
    totals = {
        o: sum(w * scores[c][o] for c, w in req.weights.items()) for o in OPTIONS if o not in vetoed
    }
    if not totals:
        raise ValueError("constraints rule out every option; relax one")
    return max(totals, key=lambda o: totals[o]), totals
