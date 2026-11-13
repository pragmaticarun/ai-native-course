# M5 · Exercise 1 — Add a replanning trigger

Plan-then-execute is cheap until reality disagrees with the plan. Each `Step` carries an
`expect` string: the step only *succeeded* if its output contains `expect`. Implement
`execute(plan, tools, replan, max_replans=2)` in `impl.py`:

- run steps in order; a step **fails** if the tool raises *or* its output lacks `expect`;
- on failure call `replan(executed, failure)` (where `executed` is the list of outputs so far
  and `failure` a short string naming the step) to get a **new list of remaining steps**,
  and continue with that list;
- return `Result(done, executed, replans)`; give up with `done=False` once more than
  `max_replans` replans would be needed.
