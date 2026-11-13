#!/usr/bin/env bash
# One command, fast, deterministic: what "done" means for this crate.
set -euo pipefail
cd "$(dirname "$0")"
cargo test --quiet --offline --features full
