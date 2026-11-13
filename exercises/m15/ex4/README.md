# Ex 15.4: turn a recorded trajectory into a deterministic regression test

The M15 worked example records every executed action (`Episode.trajectory`). A successful run is a
free regression test, if the replay is deterministic and robust to cosmetic layout changes.

Write `to_pytest(name, seed, trajectory) -> str`: Python source for a test function
`test_<name>(b)` that:

1. starts `SandboxApp(seed=<seed>)` and opens a fresh page with `ga.fresh_page(b)`;
2. replays the trajectory **by accessible name** (`ga.replay(app, page, TRAJ, "names")`), with the
   trajectory embedded as a literal (`TRAJ = [...]`, via `repr`/`pprint`), not loaded from a file;
3. asserts the *state*: `assert app.event_created()` and `assert not app.harmed()`.

Strip what makes replays brittle or leaky from each step before embedding it: drop `x`/`y` for
actions that have a `target` (names replay by target), and drop any step whose kind is `"done"`.
The tests `exec` your generated source against a real headless browser and the sandbox, on both
layouts.
