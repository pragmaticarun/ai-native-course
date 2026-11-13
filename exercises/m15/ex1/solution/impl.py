import random

INTERACTIVE = {"link", "button", "textbox"}


def annotate(elements: list[dict]) -> dict[int, dict]:
    keep = [e for e in elements if e["role"] in INTERACTIVE and e["w"] > 0 and e["h"] > 0]
    keep.sort(key=lambda e: (round(e["y"] / 10), e["x"]))
    return {i: e for i, e in enumerate(keep, 1)}


def click_point(el: dict) -> tuple[float, float]:
    return el["x"] + el["w"] / 2, el["y"] + el["h"] / 2


def _hits(x: float, y: float, elements: list[dict]) -> bool:
    return any(
        e["role"] in INTERACTIVE
        and e["x"] <= x <= e["x"] + e["w"]
        and e["y"] <= y <= e["y"] + e["h"]
        for e in elements
    )


def invalid_rate(
    elements: list[dict], targets: list[str], sigma_px: float, use_marks: bool, seed: int
) -> float:
    rng = random.Random(seed)
    marks = annotate(elements)
    by_name = {e["name"]: m for m, e in marks.items()}
    bad = 0
    for name in targets:
        cx, cy = click_point(marks[by_name[name]])
        if not use_marks:
            cx, cy = cx + rng.gauss(0, sigma_px), cy + rng.gauss(0, sigma_px)
        bad += not _hits(cx, cy, elements)
    return bad / len(targets)
