export function checkArgs(args: string[], root: string): string[] {
  // TODO: a denylist of two options is not an allowlist
  return args.filter((a) => a === "-f" || a.startsWith("http:")).map((a) => `option not allowed: ${a}`);
}
