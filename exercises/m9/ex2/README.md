# M9 · Exercise 2 — Per-tool auth scopes (TypeScript)

An MCP server behind OAuth receives a token with scopes (`media:read`, `media:delete`, ...).
Coarse "logged in or not" checks are how a read-only integration ends up able to delete.
Implement in `ts/starter/scopes.ts`:

1. `checkScopes(policy, tool, granted)` → `{ ok: true }` or `{ ok: false, missing }` where
   `missing` lists the policy's scopes for `tool` that `granted` lacks, sorted. A tool with no
   policy entry is **denied** with `missing: ["<no policy>"]`.
2. `visibleTools(policy, granted)`: the tool names the token may call, sorted (hide the rest
   from `tools/list`, so the model is never offered them).
3. `guard(policy, getGranted, tool, handler)`: wraps a tool handler. When the check fails, return
   a tool error result `{ isError: true, content: [{ type: "text", text: "insufficient scope: <missing joined by ', '>" }] }`
   without calling `handler`; otherwise call it. `getGranted(ctx)` reads the scopes for the
   current request (in production `ctx.http?.authInfo?.scopes`; the tests pass a stub).

The server must enforce this itself even if the host also filters: the host is not your
security boundary. (The SDK's `requireScopes(...)` does a coarser check at the HTTP layer;
real OAuth tokens and Client ID Metadata Documents are not exercised here: UNTESTED.)
