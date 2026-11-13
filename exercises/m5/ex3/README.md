# M5 · Exercise 3 — Downgrade a 3-agent design to one agent, and compare evals

`impl.py` contains `three_agent(facts, model)`: a researcher, a writer and a reviewer, each a
separate model call. Each hand-off passes a lossy brief, so facts get dropped. Implement:

- `single_agent(facts, model)`: one call to `model(prompt)` with **all** the facts, returning
  `(text, calls)` where `calls == 1`;
- `score(text, facts)`: fraction of facts that appear (case-insensitive substring) in `text`;
- `compare(cases, model)`: for each list of facts in `cases`, run both designs and return
  `{"three_agent": {"score": mean, "calls": total}, "single_agent": {...}}`.

`model` is any `Callable[[str], str]`; the tests pass a deterministic fake.
