class MemoryStore:
    def __init__(self) -> None:
        self.facts: dict[str, tuple[str, int]] = {}

    def remember(self, key: str, value: str, at: int) -> None:
        old = self.facts.get(key)
        if old is None or at >= old[1]:
            self.facts[key] = (value, at)

    def recall(self, key: str, now: int, max_age: int) -> str | None:
        fact = self.facts.get(key)
        if fact is None or now - fact[1] > max_age:
            return None
        return fact[0]


def audit(
    store: MemoryStore, truth: dict[str, str], now: int, max_age: int
) -> dict[str, list[str]]:
    report: dict[str, list[str]] = {"stale": [], "wrong": [], "missing": []}
    for key, real in truth.items():
        fact = store.facts.get(key)
        if fact is None:
            report["missing"].append(key)
        elif now - fact[1] > max_age:
            report["stale"].append(key)
        elif fact[0] != real:
            report["wrong"].append(key)
    return {k: sorted(v) for k, v in report.items()}
