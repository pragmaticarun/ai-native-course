# Ex 12.1: critique an adoption plan

A director hands you a 90-day plan. Before arguing about it, run it through the course ladder (M12 `ladder.py`:
Shapiro's levels plus our own entry criteria built from DORA's AI capabilities).

Implement `critique(plan, team) -> list[str]`. `team` is a `ladder.Team` (where they are now); `plan` is a dict
with `stages`, each having `target` (level), `adds` (artifacts and capabilities delivered during the stage),
`agent_prs_per_week` and `reviewer_hours_per_week` expected at the end of the stage. Return findings, in stage order,
using exactly these strings:

- `stage N: skips from L<a> to L<b>`: a stage moves up more than one level.
- `stage N: targets L5`: the course does not plan for L5.
- `stage N: missing <thing>`: an entry requirement for the stage's target level (from `ladder.ENTRY`) that neither the
  team already has nor any stage up to and including this one adds. One finding per missing item, in `ENTRY` order
  (capabilities, then artifacts). For a skipped level, check every level passed through.
- `stage N: review load <x>`: from L3 up, agent PRs × `team.review_hours_per_pr` / reviewer hours is above 0.8
  (rounded to 2 places, as in `ladder.review_load`). This is how "human-in-the-loop theater" starts.

An empty list means the plan is coherent.
