#!/usr/bin/env bash
# Optional local check before a release (loaded only when the agent needs it).
set -euo pipefail
git diff --quiet && git diff --cached --quiet
