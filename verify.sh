#!/usr/bin/env bash
# One command for "done": the same checks CI runs, offline, mock models only.
#   ./verify.sh setup      install Python/TS/site dependencies from the lockfiles
#   ./verify.sh            everything below, in order
#   ./verify.sh python|ts|rust|kmp|site|exercises
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
step() { printf '\n== %s ==\n' "$*"; }

setup() {
  step setup
  (cd python && uv sync --locked)
  pnpm install --frozen-lockfile
  (cd site && pnpm install --frozen-lockfile)
}
python_checks() {
  step python
  (cd python && uv run ruff check ../examples/python ../exercises ../projects ../scripts src \
    && uv run ruff format --check ../examples/python ../exercises ../projects ../scripts src \
    && bash ../scripts/typecheck_python.sh \
    && uv run pytest -q -rs ../examples/python \
    && uv run python ../scripts/validate_quizzes.py)
}
ts_checks() { step typescript; pnpm typecheck && pnpm test; }
exercises() {
  step exercises
  (cd python && uv run python ../scripts/check_exercises.py --lang py)
  python3 scripts/check_exercises.py --lang ts
}
rust_checks() {
  step rust
  (cd rust/media-probe && cargo fmt --check && cargo clippy --all-targets --locked -- -D warnings && cargo test --locked)
}
kmp_checks() { step kmp; (cd kmp && ./gradlew :shared:jvmTest --console=plain -q); }
site_checks() { step site; (cd site && pnpm build); }

case "${1:-all}" in
  setup) setup ;;
  python) python_checks ;;
  ts) ts_checks ;;
  exercises) exercises ;;
  rust) rust_checks ;;
  kmp) kmp_checks ;;
  site) site_checks ;;
  all) python_checks; ts_checks; exercises; rust_checks; kmp_checks; site_checks; step "all checks passed" ;;
  *) echo "usage: $0 [setup|python|ts|exercises|rust|kmp|site]" >&2; exit 2 ;;
esac
