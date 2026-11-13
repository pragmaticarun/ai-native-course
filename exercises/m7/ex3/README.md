# M7 · Exercise 3 — Bounded fan-out with retries and a failure budget (TypeScript)

The worked example's `mapLimit` (L7.4) caps concurrency and collects failures. Real media
fan-out needs two more things. Implement `fanOut(items, fn, opts)` in `ts/starter/fanout.ts`:

- At most `opts.limit` calls to `fn` in flight at any moment (throw `RangeError` if `limit < 1`).
- Results in input order, as `{ ok: true, value }` or `{ ok: false, error, attempts }`.
- Each item is tried up to `1 + opts.retries` times before it counts as failed.
- **Failure budget**: once `opts.maxFailures` items have failed permanently, start no new items;
  every item not yet started becomes `{ ok: false, error: "skipped", attempts: 0 }`. Items
  already running finish normally.
- Return `{ results, peak }` where `peak` is the highest number of concurrent `fn` calls seen.

Tests run with `EXERCISE_VARIANT=solution|starter`; CI requires the solution to pass and the
starter to fail.

C++/Rust note: this is a counting semaphore (`std::counting_semaphore`, `tokio::sync::Semaphore`)
plus a shared atomic failure counter that the dispatcher checks before taking the next permit.
