# M1 · Exercise 1 — Place three teams on two different models

Implement `place(team)` returning `{"shapiro": <0-5>, "feng": <"L1".."L5">}`.

`team` is a dict of observed facts (booleans). Use these **course rubrics**, which are
simplified readings of each source (read lessons L1.5 for the originals):

**Shapiro (how the engineering workflow uses AI)**, take the highest that applies:
- `uses_ai: False` → 0 · `delegates_discrete_tasks` → 1 · `pairs_in_flow` → 2
- `reviews_agent_diffs_mostly` → 3 · `writes_specs_and_leaves` → 4 · `no_human_code_review` → 5

**Feng et al. (the user's role towards one agent)**:
- `user_drives_every_step` → L1 Operator · `user_and_agent_share_work` → L2 Collaborator
- `agent_leads_user_advises` → L3 Consultant · `user_only_approves_key_actions` → L4 Approver
- `user_only_monitors` → L5 Observer. If several are set, take the most autonomous.

Why do one team's two placements differ? Answer in a comment in your solution.
