// M10 L10.6: an allowlist for agent shell commands. Rule shape follows Claude Code's
// `Bash(git diff *)` (trailing " *" = prefix match); deny beats allow.
export interface Policy { allow: string[]; deny: string[] }

function matches(rule: string, command: string): boolean {
  const m = rule.match(/^Bash\((.+)\)$/);
  if (!m) return false;
  const pat = m[1];
  if (pat.endsWith(" *")) {
    const prefix = pat.slice(0, -2);
    return command === prefix || command.startsWith(prefix + " ");
  }
  return command === pat;
}

export function decide(p: Policy, commandLine: string): { ok: boolean; why: string } {
  if (/\$\(|`/.test(commandLine)) return { ok: false, why: "command substitution is never auto-approved" };
  const parts = commandLine.split(/&&|\|\||;|\||\n/).map((s) => s.trim()).filter(Boolean);
  for (const part of parts) {
    if (p.deny.some((r) => matches(r, part))) return { ok: false, why: `denied: ${part}` };
    if (!p.allow.some((r) => matches(r, part))) return { ok: false, why: `not on the allowlist: ${part}` };
  }
  return { ok: true, why: "ok" };
}
