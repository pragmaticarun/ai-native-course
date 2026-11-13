#!/usr/bin/env bash
# mypy over the shared package, worked examples, scripts and every exercise variant.
# Run from python/:  bash ../scripts/typecheck_python.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EX_PATHS="$(ls -d "$ROOT"/examples/python/m* | tr '\n' ':')$ROOT/exercises"
MYPYPATH="$EX_PATHS" uv run mypy "$ROOT/python/src" "$ROOT/scripts"
for d in "$ROOT"/examples/python/m*; do
  MYPYPATH="$EX_PATHS" uv run mypy "$d"
done
for f in "$ROOT"/exercises/m*/ex*/{starter,solution}/impl.py; do
  MYPYPATH="$EX_PATHS" uv run mypy "$f" "$(dirname "$(dirname "$f")")"/tests/*.py >/dev/null \
    || { echo "mypy failed: $f"; MYPYPATH="$EX_PATHS" uv run mypy "$f"; exit 1; }
done
echo "mypy: all clean"
