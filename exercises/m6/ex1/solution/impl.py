RUBRIC = """Grade one release-notes entry for a user of the app.
5: accurate, user-facing benefit stated, mentions any action the user must take.
4: accurate and user-facing, but misses a required action or is wordy.
3: accurate but written for developers (internal names, PR jargon).
2: vague ("various fixes") or partly inaccurate.
1: wrong, misleading, or leaks internal/security details.
Reply with the score on the first line, then one sentence of justification."""


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def calibrate(judge_scores: list[int], human_pass: list[bool]) -> tuple[int, float]:
    best = (1, -2.0)
    for t in range(1, 6):
        k = cohen_kappa([s >= t for s in judge_scores], human_pass)
        if k > best[1]:
            best = (t, k)
    return best
