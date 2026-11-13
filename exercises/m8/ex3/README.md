# M8 · Exercise 3 — Version a workflow without breaking in-flight runs

`OrderV1` (given in `impl.py`) charges, then ships. Product wants a fraud check between the two.
Thousands of V1 runs are in flight (some waiting days on a human), and Temporal will replay
their recorded histories against whatever code the worker runs next.

Write `OrderV2` (same workflow name, `"Order"`) that:

- runs `fraud_check` between `charge` and `ship` **for new runs**, and
- replays every V1 history without a non-determinism error.

Use `workflow.patched("fraud-check")`. The tests record a real V1 history, replay it against your
`OrderV2` with Temporal's `Replayer`, and run a fresh V2 order to check `fraud_check` runs.
(Once no V1 runs remain you would switch to `workflow.deprecate_patch` and later remove the branch.)

C++/Rust note: like a binary log format with a version tag: old records must still decode
after the reader changes.
