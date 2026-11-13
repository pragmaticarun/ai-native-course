RUBRIC = "Grade the release note."  # TODO: anchors for 1-5


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    # TODO
    return 0.0


def calibrate(judge_scores: list[int], human_pass: list[bool]) -> tuple[int, float]:
    # TODO: pick the threshold that agrees best with humans.
    return 4, 0.0
