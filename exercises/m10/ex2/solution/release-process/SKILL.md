---
name: release-process
description: Cuts a new release of the app (version bump, changelog, tag, push) using the release tool. Use when asked to cut, ship or publish a release or a new version.
metadata:
  owner: release-team
---

# Cut a release

1. `release check-clean` (stop if it fails: commit or stash first)
2. `release run-tests` (stop on any failure; never skip tests to ship)
3. `release bump <version>`
4. `release changelog <version>`; then edit the entry so user-visible changes come first
5. `release tag v<version>`
6. `release push`

If a step fails after the tag exists, don't delete the tag; tell a human. For a quick local check first, run
scripts/preflight.sh.
