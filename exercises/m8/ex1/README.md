# M8 · Exercise 1 — Make a non-idempotent tool safe to retry

`PaymentsAPI.charge(account, cents, idempotency_key=None)` (in the tests) charges a card. Like many
real APIs it sometimes **times out after the charge went through**. A durable runtime (Temporal,
LangGraph checkpoints, Pydantic AI on Temporal) will retry the step, so a naive tool charges twice.

Implement `safe_charge(api, store, run_id, step, account, cents, *, attempts=3)` in `impl.py`:

1. Derive a deterministic idempotency key from the run and step: `f"{run_id}:{step}"`.
   (Never a random UUID per attempt: a retry must reuse the key.)
2. If `store` (a dict) already holds a result for the key, return it without calling the API.
3. Call `api.charge(..., idempotency_key=key)`, retrying on `TimeoutError` up to `attempts`
   calls. The API deduplicates on the key, so a retry after a timeout returns the first charge.
4. Save the result in `store[key]` and return it. If every attempt times out, raise `TimeoutError`.
5. If the same key is used with a different `account`/`cents`, raise `ValueError` (a bug, not a retry).
   Store the request alongside the result to detect it.

C++/Rust note: the same idea as an exactly-once outbox: an idempotency key turns at-least-once
delivery into effectively-once processing.
