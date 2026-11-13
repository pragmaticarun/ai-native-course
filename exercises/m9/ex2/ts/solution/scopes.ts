export type Policy = Record<string, string[]>;
export type Check = { ok: true } | { ok: false; missing: string[] };
type ToolResult = { content: { type: "text"; text: string }[]; isError?: boolean };

export function checkScopes(policy: Policy, tool: string, granted: string[]): Check {
  const needed = policy[tool];
  if (needed === undefined) return { ok: false, missing: ["<no policy>"] };
  const have = new Set(granted);
  const missing = needed.filter((s) => !have.has(s)).sort();
  return missing.length === 0 ? { ok: true } : { ok: false, missing };
}

export function visibleTools(policy: Policy, granted: string[]): string[] {
  return Object.keys(policy)
    .filter((t) => checkScopes(policy, t, granted).ok)
    .sort();
}

export function guard<A, C>(
  policy: Policy,
  getGranted: (ctx: C) => string[],
  tool: string,
  handler: (args: A, ctx: C) => Promise<ToolResult>,
): (args: A, ctx: C) => Promise<ToolResult> {
  return async (args, ctx) => {
    const check = checkScopes(policy, tool, getGranted(ctx));
    if (!check.ok) {
      return { isError: true, content: [{ type: "text", text: `insufficient scope: ${check.missing.join(", ")}` }] };
    }
    return handler(args, ctx);
  };
}
