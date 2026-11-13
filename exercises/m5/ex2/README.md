# M5 · Exercise 2 — Make an approval gate meaningful

An approval button that people click without reading is "HITL theater". Implement in `impl.py`:

- `make_request(old, new, action, requester)`: return a `Request` with a unified `diff`
  (`difflib.unified_diff` of the lines, `lineterm=""`, joined by `"\n"`), a `summary` like
  `"+2 -1 lines"` (count added/removed lines, not the `+++`/`---` headers), the `action`,
  the `requester`, and `diff_hash` = SHA-256 hex digest of the diff text.
- `accept(request, decision)`: return `None` if the decision may proceed, else a short
  reason string. Reject when: the reviewer is the requester; an **approval** has a reason
  shorter than 3 words; or `decision.seen_hash` doesn't match `request.diff_hash` (they
  approved a different diff than the one in front of them). Rejections (`approved=False`)
  only need a reviewer who isn't the requester.
