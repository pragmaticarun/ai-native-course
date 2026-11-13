# M8 · Exercise 2 — An approval that arrives days later (Temporal)

Write the `PublishWithApproval` workflow in `impl.py`. It models "the agent prepared a release;
a human must approve it before it goes live":

- `run(title)` waits for a decision for up to **7 days** (`workflow.wait_condition(...,
  timeout=timedelta(days=7))`), then returns:
  - `"published <title> (approved by <reviewer>)"` after an `approve(reviewer)` signal,
  - `"rejected: <reason>"` after a `reject(reason)` signal,
  - `"expired"` if nothing arrives within 7 days.
- A `status()` query returns `"waiting"`, `"approved"`, `"rejected"` or `"expired"`.

The tests use Temporal's time-skipping test server: "three days later" takes milliseconds.
Nothing runs while the workflow waits: no worker thread, no polling loop, no cost.

Use exactly these names: `@workflow.defn(name="PublishWithApproval")`, signals `approve` and
`reject`, query `status`.

C++/Rust note: durable execution is event sourcing plus deterministic replay (like `rr`):
the wait is an event in the history, not a sleeping thread.
