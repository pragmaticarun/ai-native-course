# Projects

End-to-end projects (see SYLLABUS.md section 5). Each one has:

- `spec/`: the brief and milestones;
- `common/`: the provided kit (fixtures, harness) that both versions use;
- `starter/`: what you start from (the evals fail until you finish the TODOs);
- `solution/`: the reference solution (the evals pass);
- `evals/`: the tests. CI runs them against both versions and requires the solution to pass
  and the starter to fail (`scripts/check_exercises.py`).

Run one project's evals: `cd python && PROJECT_VARIANT=starter uv run pytest ../projects/p1/evals`.
