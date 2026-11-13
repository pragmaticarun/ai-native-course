---
name: release-notes
description: Drafts release notes from merged pull requests and the changelog. Use when the user asks for release notes, a changelog entry, or "what shipped" for a version.
license: Apache-2.0
metadata:
  owner: platform-team
---

# Release notes

1. Run `scripts/merged_prs.py <from-tag> <to-tag>` to list merged PRs with labels.
2. Group them by label using the table in references/LABELS.md.
3. Write the notes in the house style: one line per change, user-visible changes first.
4. Never invent a change that isn't in the PR list.
