# timecode — agent instructions

Verify: `./verify.sh`

- `verify.sh` runs `cargo test --features full`. Plain `cargo test` compiles none of the
  integration tests and still prints a green result.
- Before a PR, also run `cargo fmt --check` and `cargo clippy --all-targets --features full -- -D warnings`.
- Timecodes are non-drop-frame only. Don't add drop-frame logic without a spec.
- Keep the public API in `src/lib.rs`; no new dependencies without asking.
