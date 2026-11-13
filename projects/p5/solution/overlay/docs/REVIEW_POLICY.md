# Review policy (agent and human PRs)

- At most 400 changed lines (lockfiles excluded); split bigger work into stacked PRs.
- Agent PRs carry the `agent-authored` label or an `Agent-Session:` trailer, and the
  output of `./verify.sh`. An AI pre-review runs before a human is asked.
- The person who prompted the agent can't be the only approver.
- Changes under `.github/` or `rust/` need two approvals.
- Review load: if agent PRs would take more than 80% of reviewer time, slow the agents down
  rather than skim.
