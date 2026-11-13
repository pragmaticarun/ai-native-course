export type Policy = Record<string, string[]>;
export type Check = { ok: true } | { ok: false; missing: string[] };
type ToolResult = { content: { type: "text"; text: string }[]; isError?: boolean };

export function checkScopes(policy: Policy, tool: string, granted: string[]): Check {
  // TODO
  void policy;
  void tool;
  void granted;
  return { ok: true };
}

export function visibleTools(policy: Policy, granted: string[]): string[] {
  // TODO
  void granted;
  return Object.keys(policy).sort();
}

export function guard<A, C>(
  policy: Policy,
  getGranted: (ctx: C) => string[],
  tool: string,
  handler: (args: A, ctx: C) => Promise<ToolResult>,
): (args: A, ctx: C) => Promise<ToolResult> {
  // TODO
  void policy;
  void getGranted;
  void tool;
  return handler;
}
