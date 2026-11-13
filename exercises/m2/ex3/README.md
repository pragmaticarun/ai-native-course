# M2 · Exercise 3 — Stream partial structured output

Models stream JSON a few characters at a time. Implement `parse_partial(prefix)` that
returns the best-effort `dict` for an incomplete JSON object prefix, so a UI can show
fields as they arrive:

- complete the prefix by closing an open string, then any open `[` / `{` (innermost first);
- drop a dangling key with no value yet (`{"a": 1, "b"` → `{"a": 1}`) and a trailing comma
  or colon;
- return `{}` if nothing parseable is available yet.

You only need to support objects, arrays, strings (no escaped quotes), numbers, `true`,
`false`, `null`. Numbers may be cut mid-way; keep what parses.
