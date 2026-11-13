---
name: add-lesson
description: Adds a lesson page with a tested example to a course module. Use when asked to write a new lesson, worked example or exercise for this course.
---

# Add a lesson

1. Put the code in `examples/python/mX/` (and `examples/ts/mX/` if there is a TS tab) with a test next to it.
2. Write the page under `site/src/content/docs/<section>/mX/` and embed the code with `<Snippet path=...>`.
3. Exercises: `exercises/mX/exY/{README.md,starter/,solution/,tests/}`; the starter must fail the tests.
4. Add quiz questions to `quizzes/mX.yaml` and run `uv run python ../scripts/validate_quizzes.py` from `python/`.
5. Label anything you could not run as untested, and add a CHANGELOG.md line.
6. Finish with the `verify-course` skill.
