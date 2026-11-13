import re


def _norm(s: str) -> list[str]:
    return re.sub(r"[^\w\s']", "", s.lower()).split()


def _edits(r: list[str], h: list[str]) -> int:
    prev = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        cur = [i] + [0] * len(h)
        for j, hw in enumerate(h, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rw != hw))
        prev = cur
    return prev[-1]


def wer(ref: str, hyp: str) -> float:
    r, h = _norm(ref), _norm(hyp)
    if not r:
        return 0.0 if not h else 1.0
    return _edits(r, h) / len(r)


def corpus_wer(pairs: list[tuple[str, str]]) -> float:
    edits = sum(_edits(_norm(r), _norm(h)) for r, h in pairs)
    return edits / max(sum(len(_norm(r)) for r, _ in pairs), 1)


def choose(runs: list[dict], max_wer: float, max_rtf: float) -> dict | None:
    scored = [(r, corpus_wer([(u["ref"], u["hyp"]) for u in r["utterances"]])) for r in runs]
    ok = [(r, w) for r, w in scored if w <= max_wer and r["rtf"] <= max_rtf]
    if not ok:
        return None
    return min(ok, key=lambda rw: (rw[0]["rtf"], rw[1]))[0]
