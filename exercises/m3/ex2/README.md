# M3 · Exercise 2 — Detect and break repetition loops

The example's detector only catches the *same* call repeated. Real agents also cycle:
`open A → open B → open A → open B …`. Implement `find_cycle(calls, min_repeats=3)`:

- `calls` is a list of strings like `"read:{\"path\": \"a\"}"` (oldest first);
- look at the **end** of the list for a block of length 1, 2 or 3 that repeats back-to-back
  at least `min_repeats` times; return the shortest such block as a list, else `None`.

Then `should_stop(calls)` returns `True` when `find_cycle` finds one.
