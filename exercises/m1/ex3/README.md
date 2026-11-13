# M1 · Exercise 3 — A one-page "next level" plan, generated

Using `assess.py` from the M1 worked example (`Worksheet`, `GATES`, `sustainable_level`),
implement `next_level_plan(ws)` returning a list of strings:

1. If the observed `workflow_level` is above the sustainable level, the **first** item is
   `"Stabilise at L<sustainable>: raise <capability> to 2"` for each missing gate of the
   *observed* level (one item per capability, lowest score first, ties by name).
2. Otherwise target `min(workflow_level + 1, 5)` and add one item
   `"Raise <capability> from <score> to 2"` per missing gate of the target, lowest score
   first, ties by name.
3. If nothing is missing, return `["Ready for L<target>: run a two-week pilot and measure"]`.

Remember: the gates are the course's synthesis, not an official standard.
