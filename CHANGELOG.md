# Changelog

All notable changes to the course. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-11-13

### Content
- Modules **M0–M3** built: 19 lessons, worked examples in Python and TypeScript, 11 exercises with CI-tested solutions, 4 quizzes (29 questions).
- Syllabus v0.3 published as the [syllabus page](https://pragmaticarun.github.io/ai-native-course/syllabus/).

### Dependency pins
- Python 3.13: `pydantic 2.14.3`, `pydantic-ai-slim 2.68.0`, `pyyaml 6.0.3`; dev: `pytest 9.2.0`, `ruff 0.17.5`, `mypy 2.4.1`.
- TypeScript: `ai 7.0.170` (syllabus planned 7.0.172; it was published less than 24 h before this release and pnpm 12's default minimum-release-age policy rejects it, so we pinned the previous release), `zod 4.6.7`, `typescript 7.0.2`, `vitest 5.1.0`.
- Site: `astro 7.4.11`, `@astrojs/starlight 0.42.11`, `starlight-links-validator 0.27.0`.

### Known gaps
- Device/emulator steps (adb mobile-use, Android/KMP) are marked **untested**; only their parsing logic runs in CI.
- Live-provider (`--live`) paths are not exercised in CI (no API keys stored).
