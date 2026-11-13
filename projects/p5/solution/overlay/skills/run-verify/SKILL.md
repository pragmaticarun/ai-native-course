---
name: run-verify
description: Run the repo's checks and read failures. Use when you finish a change, before opening a PR, or when CI fails.
---

# Run verify

1. Run `./verify.sh` from the repo root.
2. If Python fails, rerun just that file: `python -m pytest -q -c py/pytest.ini py/tests/<file>`.
3. If TypeScript fails: `node --experimental-strip-types --test web/test/<file>.test.ts`.
4. If Rust fails: `cargo test --manifest-path rust/clipcore/Cargo.toml <name>`.
5. Paste the last lines of a passing run into the PR under "How it was checked".
