#!/usr/bin/env bash
# The one command that says "done" (CI runs it too). Fast: no network, no sleeps.
set -euo pipefail
cd "$(dirname "$0")"
"${PYTHON:-python3}" -m pytest -q -c py/pytest.ini py/tests
node --experimental-strip-types --no-warnings --test web/test/*.test.ts
cargo test --quiet --offline --manifest-path rust/clipcore/Cargo.toml
