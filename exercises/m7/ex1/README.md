# M7 · Exercise 1 — Retry with exponential backoff and full jitter

Graph frameworks give you a retry policy per node (LangGraph's `RetryPolicy`), but you should
know what it does. Implement it yourself in `impl.py`:

1. `backoff_delays(attempts, base, cap, rng)`: the sleep before each *retry* (so
   `attempts - 1` values). Retry *i* (0-based) sleeps `rng.uniform(0, min(cap, base * 2**i))`
   ("full jitter": spreads retries so many clients don't hammer a provider in lockstep).
2. `retry(fn, *, attempts, base, cap, rng, sleep, retry_on)`: call `fn()`; on an exception
   that is an instance of one of `retry_on`, sleep the next delay and try again, up to
   `attempts` calls in total. Re-raise the last error when attempts run out. Exceptions not in
   `retry_on` propagate immediately (no sleep, no retry). Return `fn()`'s value on success.

`sleep` is injected so tests run instantly; take delays from `backoff_delays` with the same
`rng` so they are reproducible.

C++/Rust note: same shape as `backoff` crates or a hand-rolled loop around `std::this_thread::sleep_for`;
the injected `sleep` plays the role of a mockable clock.
