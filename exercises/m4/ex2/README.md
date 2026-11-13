# M4 · Exercise 2 — A memory store, and an eval that catches stale memory

Long-term memory goes wrong quietly: an old fact keeps being used after the world changed.
Implement in `impl.py`:

- `MemoryStore.remember(key, value, at)`: store a fact with its time. A fact with an **older**
  `at` than the stored one must NOT overwrite it (events can arrive out of order).
- `MemoryStore.recall(key, now, max_age)`: the value, or `None` if missing or older than
  `max_age` seconds at time `now`.
- `audit(store, truth, now, max_age)`: compare memory against `truth` (a dict of the real
  current values) and return `{"stale": [...], "wrong": [...], "missing": [...]}` (sorted
  key lists). *stale* = present but too old; *wrong* = fresh but different from the truth;
  *missing* = in `truth` but not in memory at all.
