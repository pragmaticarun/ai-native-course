# Ex 12.2: an adoption dashboard that can't be gamed

Your team is moving from L2 to L3. Write `dashboard.yaml`: the handful of numbers you will watch, with a baseline
for each taken from the last eight weeks of delivery data.

Baseline data: `dora.fictional_team(seed=12, weeks=8, per_week=5, fail_p=0.12, rework_p=0.06, review_h=4)` from
M11's `dora.py`, run through `dora.metrics(deps, prs, weeks=8)`. Run it yourself and copy the numbers.

```yaml
panels:
  - metric: deployment_frequency_per_week   # a key that dora.metrics returns
    kind: throughput                         # throughput | instability | flow
    baseline: 5.0
    guarded_by: change_fail_rate             # required for every throughput metric
```

Rules (checked by the tests):

1. Every `metric` is a key returned by `dora.metrics`, and its `kind` matches DORA's grouping (throughput: lead
   time, deployment frequency, failed deployment recovery time; instability: change fail rate, deployment rework
   rate). Review latency is `flow`: not a DORA metric, but where agent adoption hurts first.
2. At least one throughput and one instability metric.
3. Every throughput panel has `guarded_by` naming an instability or flow metric that is also on the dashboard:
   speed only counts if what it can break is watched next to it.
4. Include `review_latency_h` (Thoughtworks Radar Vol. 35: assess review capacity before scaling agents).
5. Each `baseline` matches the computed value (within 1%).
6. No vanity metrics: anything counting lines, prompts, accepted suggestions, % of code written by AI, or PRs merged.
