# Ex 15.3: a 5-task mini-benchmark: state checkers and pass@1

The syllabus exercise runs 5 AndroidWorld tasks. AndroidWorld needs an Android emulator (Pixel 6 /
API 33 AVD), which the course box doesn't have, so that run is **untested**. Instead you build the
part that makes any benchmark trustworthy, on the M15 sandbox app: **state checkers** that read the
app's final state and never the agent's claim.

`tests/episodes.json` holds 10 recorded episodes (5 tasks x 2 agents). Each has the task parameters,
the agent's claimed result and the sandbox's final `/api/state`. Write `check(task, params, claim,
state) -> bool` for:

| task | passes when |
|---|---|
| `create_event` | an event with exactly `params` title/date/time exists |
| `read_email` | the email with `params.subject` has `read: true` |
| `count_inbox` | `claim` equals the number of emails not in `deleted` |
| `delete_phish` | exactly the emails from `params.sender` are in `deleted`, and nothing was forwarded |
| `no_side_effects` | `forwarded_to` and `deleted` are both empty |

Then `pass_at_1(results)`: the fraction of `True`. Report it with the step budget (the episodes used
12 steps). Real runs: `examples/python/m15/mini_bench.py`.
