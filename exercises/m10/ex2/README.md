# Ex 10.2: a skill that teaches your release process

Your team cuts releases by hand and agents keep getting the order wrong. Write `release-process/SKILL.md`
(Agent Skills format) so that an agent can find it and follow it.

The release tool used in this exercise (`release ...`, simulated by the tests) enforces your team's rules:

- `release check-clean` must come first (no uncommitted changes);
- `release run-tests` must pass before anything changes;
- `release bump <version>`, then `release changelog <version>`, then `release tag v<version>`;
- `release push` comes last, and only after the tag.

The tests:

1. validate the skill against the spec (`skills.validate_skill`: name rules, matching folder, a description that
   says **when** to use it);
2. give a mock agent the task "Cut release 1.4.0 of the app": it must pick your skill from the catalog by its
   description, then run every backticked `release ...` command in your numbered steps, in order, with `<version>`
   replaced by `1.4.0`;
3. check the simulated repo ends tagged and pushed at `v1.4.0`, with a changelog entry.

Bonus (not tested): add `scripts/preflight.sh` and reference it from the body, so the agent loads it only when needed.
