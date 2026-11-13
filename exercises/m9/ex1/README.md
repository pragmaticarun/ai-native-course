# M9 · Exercise 1 — An `input_required` confirmation

Write `build_server(published)` in `impl.py`: an `MCPServer` named `"publisher"` with one tool,
`publish(video_id: str, channel: str) -> str`, that must **ask the user before publishing**:

- The question is an elicitation with the message `"Publish <video_id> to <channel>?"` and a
  boolean field `confirm` (use a Pydantic model with `confirm: bool`).
- Only when the user accepts **and** `confirm` is true: append `(video_id, channel)` to
  `published` and return `"published <video_id> to <channel>"`.
- Otherwise (declined, cancelled, or `confirm` false) return `"cancelled"`.
- Annotate the tool as destructive (`ToolAnnotations(destructive_hint=True)`); it is not read-only.

Use the SDK's resolver pattern (`Annotated[ElicitationResult[...], Resolve(fn)]` with
`fn` returning `Elicit(...)`) so one handler serves both protocol revisions: on 2026-07-28
the question goes back as an `input_required` result (multi round-trip request), on
2025-11-25 as an `elicitation/create` request. The tests check both. Define the resolver at
module level.
