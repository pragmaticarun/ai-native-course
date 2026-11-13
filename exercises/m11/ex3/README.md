# Ex 11.3: a review checklist for agent PRs, applied to three PRs

Agents produce plausible code fast; reviewers need a short, mechanical checklist so they can spend their attention
on design. Implement the five checks in `CHECKS` (each takes a `PR` and returns `True` when the PR passes) and
`apply(pr)`, which returns `{check_name: passed}` for every check.

A `PR` has `files`: `{path: added_text}` (only the added lines, joined with newlines) and `deleted`: paths removed.

1. **`tests-with-code`**: if any file under `src/` changed, some file under `tests/` changed too.
2. **`pinned-deps`**: no added dependency line in `pyproject.toml`, `requirements*.txt` or `package.json` uses a
   range: `>=`, `~=`, `^`, `~`, `*`, `>` or `<`. (Exact pins: `==` in Python, a bare version in package.json.)
3. **`todo-has-issue`**: every added `TODO`/`FIXME` mentions an issue as `#<number>`.
4. **`reversible-migration`**: every added file under `migrations/` that defines `upgrade` also defines `downgrade`.
5. **`no-deleted-tests`**: no path under `tests/` is deleted.

The tests apply your checklist to three agent PRs from a fictional repo and compare with a human reviewer's verdicts.
