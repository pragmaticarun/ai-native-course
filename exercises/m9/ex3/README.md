# M9 · Exercise 3 — Contract tests against both spec revisions

Clients in the wild speak 2025-11-25 (the `initialize` handshake) or 2026-07-28 (stateless,
`server/discover`). A server change can pass on one and break on the other. Write the checks.

1. `contract_violations(client)` (async) returns a sorted list of strings, one per problem:
   - `"<tool>: no description"` when a tool's description is empty or missing;
   - `"<tool>: destructive without destructiveHint"` when a tool's name starts with `delete_`,
     `remove_` or `drop_` and its annotations don't set `destructive_hint=True`;
   - `"<tool>: sample call failed"`: for each tool listed in `SAMPLE_ARGS` (and present on
     the server), call it with `SAMPLE_ARGS[tool]`; report it when the result has `is_error`
     or the call raises (the Python client raises when structured output doesn't match the
     tool's `outputSchema`, and on protocol errors).
2. `check_both(make_server)` (async) runs `contract_violations` once per revision, with a
   fresh server from `make_server()` each time, using `Client(server, mode="auto")` and
   `Client(server, mode="legacy")`, and returns `{negotiated_protocol_version: violations}`.

The tests run a good server (no violations on either revision) and a sloppy one.

C++/Rust note: MCP is to agents what LSP is to editors: a JSON-RPC protocol with versioned
capabilities. Contract tests are the conformance suite you run against every server you ship.
