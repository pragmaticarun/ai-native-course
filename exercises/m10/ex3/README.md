# Ex 10.3: find the agent-hostile traits

The structural audit in L10.5 checks for an AGENTS.md, a verify command and lockfiles. Some traits only show up in
the code. Implement `find_hostile(repo)` to report three of them, as `{trait: sorted list of relative paths}`:

- **`interactive-prompt`**: a setup or helper script that waits for a human: shell `read` (e.g. `read -p`) or Python
  `input(`. An agent running it hangs until a timeout.
- **`flaky-test`**: a test file that sleeps (`time.sleep(` / `sleep(`), uses `random` without seeding it
  (`random.seed(`), or calls a real `http://` / `https://` URL. Agents can't tell your flake from their bug.
- **`swallowed-error`**: `except:` or `except Exception:` followed by `pass` on the next line. The agent sees
  success where there was a failure.

Only look at `*.sh` and `*.py` files, and skip any `.git` directory. Traits with no hits are left out of the result.
`tests/fixtures/hostile/` has one of each (plus near-misses); `tests/fixtures/clean/` has none.
