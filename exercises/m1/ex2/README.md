# M1 · Exercise 2 — Ladder or map? Which scope?

Implement `classify(fw)` for a framework description dict with keys
`ordered_levels` (bool), `subject` (`"organisation" | "engineering_team" | "agent"`) and
`publisher_sells_platform` (bool). Return a dict:

- `kind`: `"ladder"` if the framework has ordered levels, else `"map"`.
- `scope`: the `subject` value.
- `vendor_bias_check`: `True` when the publisher sells the cloud/AI platform the
  framework recommends (you should read it looking for product steering).

Then make the tests' table of the frameworks from lesson L1.2–L1.5 come out right.
