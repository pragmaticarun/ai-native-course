# M4 · Exercise 1 — Compaction with a fidelity test

Summaries lose exactly the details that matter: decisions, constraints, numbers.
Implement in `impl.py`:

- `compact(history, keep_last, summarise)`: `history` is a list of strings (oldest first).
  Keep the last `keep_last` entries verbatim. Replace everything older with **one** entry:
  `"SUMMARY: " + summarise(older)`, followed by every older line that starts with
  `DECISION:`, `CONSTRAINT:` or `FACT:`, each on its own line and copied verbatim.
  If there is nothing older, return the history unchanged.
- `fidelity(original, compacted)`: the fraction (0.0–1.0) of pinned lines in `original`
  that still appear somewhere in `compacted`. Return `1.0` when there are no pinned lines.

The tests use a deliberately lossy summariser, so only your pin-copying keeps fidelity at 1.0.
