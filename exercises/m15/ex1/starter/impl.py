def annotate(elements: list[dict]) -> dict[int, dict]:
    return dict(enumerate(elements))  # TODO: interactive only, reading order, from 1


def click_point(el: dict) -> tuple[float, float]:
    return el["x"], el["y"]  # TODO: top-left corner is not the centre


def invalid_rate(
    elements: list[dict], targets: list[str], sigma_px: float, use_marks: bool, seed: int
) -> float:
    return 0.0  # TODO: simulate the clicks
