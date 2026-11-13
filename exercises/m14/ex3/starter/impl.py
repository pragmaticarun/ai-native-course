def wer(ref: str, hyp: str) -> float:
    r, h = ref.split(), hyp.split()
    return sum(a != b for a, b in zip(r, h, strict=False)) / max(
        len(r), 1
    )  # TODO: misses insertions/deletions  # noqa: E501


def corpus_wer(pairs: list[tuple[str, str]]) -> float:
    return sum(wer(r, h) for r, h in pairs) / len(pairs)  # TODO: not word-weighted


def choose(runs: list[dict], max_wer: float, max_rtf: float) -> dict | None:
    return min(runs, key=lambda r: r["rtf"])
