---
name: verify-course
description: Runs this course repo's full offline check (lint, types, tests, exercises, quizzes, Rust, Kotlin, site build). Use before committing or pushing, or when asked whether the repo is green.
compatibility: Needs uv, pnpm 12 with Node 24, a Rust toolchain, and JDK 21 for the Kotlin part.
---

# Verify the course

1. Run `./verify.sh setup` once per checkout.
2. Run `./verify.sh`. It stops at the first failing part and prints its name.
3. To re-run one part: `./verify.sh python` (or `ts`, `exercises`, `rust`, `kmp`, `site`).
4. Report counts from the output (pytest "N passed", vitest "Tests N passed", exercise suites).
   Say which parts you did not run and why; never report a part as passing without running it.
