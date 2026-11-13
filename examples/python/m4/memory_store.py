"""L4.3: long-term memory as a plain, inspectable store.

* semantic memory: facts keyed by subject ("user.editor" -> "neovim"), with
  `updated_at` so newer facts supersede older ones;
* episodic memory: an append-only log of what happened, searchable by keyword.

It is a JSON file on purpose: you can read it, diff it, and delete from it. Use
vector search only when keyword or key lookup demonstrably fails (see L4.4).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Fact:
    key: str
    value: str
    updated_at: int  # unix seconds (passed in, so tests control time)
    source: str = ""


@dataclass(frozen=True)
class Episode:
    at: int
    text: str


class MemoryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.facts: dict[str, Fact] = {}
        self.episodes: list[Episode] = []
        if path and path.exists():
            data = json.loads(path.read_text())
            self.facts = {f["key"]: Fact(**f) for f in data["facts"]}
            self.episodes = [Episode(**e) for e in data["episodes"]]

    def remember(self, key: str, value: str, at: int, source: str = "") -> None:
        old = self.facts.get(key)
        if old is None or at >= old.updated_at:  # newer wins; late-arriving old facts don't
            self.facts[key] = Fact(key, value, at, source)
        self.log(at, f"remember {key}={value}")

    def recall(self, key: str) -> str | None:
        fact = self.facts.get(key)
        return fact.value if fact else None

    def log(self, at: int, text: str) -> None:
        self.episodes.append(Episode(at, text))

    def search_episodes(self, word: str) -> list[Episode]:
        return [e for e in self.episodes if word.lower() in e.text.lower()]

    def save(self) -> None:
        assert self.path, "no path configured"
        data = {
            "facts": [asdict(f) for f in self.facts.values()],
            "episodes": [asdict(e) for e in self.episodes],
        }
        self.path.write_text(json.dumps(data, indent=2))

    def as_context(self, keys: list[str]) -> str:
        """Only the facts relevant to this task go into the prompt, with their age."""
        lines = [
            f"- {k}: {self.facts[k].value} (as of {self.facts[k].updated_at})"
            for k in keys
            if k in self.facts
        ]
        return "Known facts:\n" + "\n".join(lines) if lines else ""


if __name__ == "__main__":
    store = MemoryStore()
    store.remember("user.device", "Galaxy A73", at=100)
    store.remember("user.editor", "vim", at=100)
    store.remember("user.editor", "neovim", at=200)
    print(store.as_context(["user.device", "user.editor"]))
