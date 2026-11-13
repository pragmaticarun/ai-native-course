"""L4.4: retrieval done right, with no external services.

* chunk files by lines with overlap, keeping `path:start-end` for citations;
* lexical search: BM25 over identifier-aware tokens;
* "dense" search: a hashed character-trigram vector. This is a STAND-IN for a
  real embedding model so the example runs offline. It captures spelling
  similarity, not meaning; swap in a real embedding model for semantic recall;
* hybrid: reciprocal rank fusion (RRF) of the two rankings;
* rerank: a cheap second pass (here: exact-phrase and identifier bonuses).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    path: str
    start: int  # 1-based line numbers, inclusive
    end: int
    text: str

    @property
    def cite(self) -> str:
        return f"{self.path}:{self.start}-{self.end}"


def chunk_lines(path: str, text: str, size: int = 40, overlap: int = 10) -> list[Chunk]:
    lines = text.splitlines()
    chunks: list[Chunk] = []
    step = max(1, size - overlap)
    for start in range(0, max(1, len(lines)), step):
        block = lines[start : start + size]
        if not block:
            break
        chunks.append(Chunk(path, start + 1, start + len(block), "\n".join(block)))
        if start + size >= len(lines):
            break
    return chunks


_WORD = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Split snake_case and camelCase so `parseConfig` matches `parse config`."""
    out: list[str] = []
    for word in _WORD.findall(text):
        parts = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", word) or [word]
        out.extend(p.lower() for p in parts)
    return out


class BM25:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.docs = [Counter(tokenize(c.text)) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / max(1, len(self.lengths))
        df: Counter[str] = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def search(self, query: str, k: int = 5) -> list[Chunk]:
        q = tokenize(query)
        scores = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in q:
                if t in d:
                    tf = d[t]
                    norm = self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg)
                    s += self.idf[t] * tf * (self.k1 + 1) / (tf + norm)
            scores.append((s, i))
        ranked = sorted((x for x in scores if x[0] > 0), key=lambda x: (-x[0], x[1]))
        return [self.chunks[i] for _, i in ranked[:k]]


def trigram_vector(text: str, dims: int = 512) -> list[float]:
    vec = [0.0] * dims
    s = f"  {text.lower()}  "
    for i in range(len(s) - 2):
        vec[hash_trigram(s[i : i + 3]) % dims] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def hash_trigram(t: str) -> int:
    h = 2166136261  # FNV-1a: deterministic across runs (Python's hash() is salted)
    for ch in t.encode():
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return h


class TrigramIndex:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.vectors = [trigram_vector(c.text) for c in chunks]

    def search(self, query: str, k: int = 5) -> list[Chunk]:
        q = trigram_vector(query)
        scores = [
            (sum(a * b for a, b in zip(q, v, strict=True)), i) for i, v in enumerate(self.vectors)
        ]
        ranked = sorted(scores, key=lambda x: (-x[0], x[1]))
        return [self.chunks[i] for _, i in ranked[:k]]


def rrf(rankings: list[list[Chunk]], k: int = 60, top: int = 5) -> list[Chunk]:
    """Reciprocal rank fusion: score = sum 1/(k + rank). Robust, no score calibration."""
    scores: dict[str, float] = {}
    by_cite: dict[str, Chunk] = {}
    for ranking in rankings:
        for rank, c in enumerate(ranking, start=1):
            scores[c.cite] = scores.get(c.cite, 0.0) + 1.0 / (k + rank)
            by_cite[c.cite] = c
    order = sorted(scores, key=lambda cite: (-scores[cite], cite))
    return [by_cite[c] for c in order[:top]]


def rerank(query: str, chunks: list[Chunk]) -> list[Chunk]:
    q = query.lower()
    idents = [w for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]+", query) if "_" in w or w != w.lower()]

    def bonus(c: Chunk) -> float:
        text = c.text.lower()
        return (2.0 if q in text else 0.0) + sum(1.0 for i in idents if i.lower() in text)

    return sorted(chunks, key=lambda c: -bonus(c))  # stable: ties keep fused order


def answer_with_citations(query: str, chunks: list[Chunk]) -> str:
    if not chunks:
        return "I could not find this in the indexed files."
    return f"See {chunks[0].cite}" + "".join(f"; also {c.cite}" for c in chunks[1:2])
