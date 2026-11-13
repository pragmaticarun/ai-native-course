class MemoryStore:
    def __init__(self) -> None:
        self.facts: dict[str, tuple[str, int]] = {}

    def remember(self, key: str, value: str, at: int) -> None:
        # TODO: don't let older facts overwrite newer ones.
        self.facts[key] = (value, at)

    def recall(self, key: str, now: int, max_age: int) -> str | None:
        # TODO: respect max_age.
        fact = self.facts.get(key)
        return fact[0] if fact else None


def audit(
    store: MemoryStore, truth: dict[str, str], now: int, max_age: int
) -> dict[str, list[str]]:
    # TODO
    return {"stale": [], "wrong": [], "missing": []}
