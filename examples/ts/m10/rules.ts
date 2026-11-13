// M10 L10.3: AGENTS.md chains and Cursor .mdc rule selection (TypeScript tab).
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";

export function globToRegExp(pattern: string): RegExp {
  let out = "";
  for (let i = 0; i < pattern.length; ) {
    if (pattern.startsWith("**/", i)) { out += "(?:.*/)?"; i += 3; }
    else if (pattern.startsWith("**", i)) { out += ".*"; i += 2; }
    else if (pattern[i] === "*") { out += "[^/]*"; i += 1; }
    else if (pattern[i] === "{") {
      const end = pattern.indexOf("}", i);
      out += "(?:" + pattern.slice(i + 1, end).split(",").map(esc).join("|") + ")";
      i = end + 1;
    } else { out += esc(pattern[i]); i += 1; }
  }
  return new RegExp(`^${out}$`);
}
const esc = (s: string) => s.replace(/[.+?^${}()|[\]\\]/g, "\\$&");

/** AGENTS.md files that apply to `file`, root first (the closest one is read last and wins). */
export function agentsChain(repo: string, file: string): string[] {
  const chain: string[] = [];
  for (let d = dirname(join(repo, file)); ; d = dirname(d)) {
    if (existsSync(join(d, "AGENTS.md"))) chain.unshift(relative(repo, join(d, "AGENTS.md")));
    if (d === repo || d === dirname(d)) break;
  }
  return chain;
}

export type Mode = "always" | "auto-attached" | "agent-requested" | "manual";
export interface Rule { name: string; description?: string; globs: string[]; alwaysApply: boolean }

export function parseMdc(name: string, text: string): Rule {
  const fm = text.startsWith("---\n") ? text.slice(4, text.indexOf("\n---", 4)) : "";
  const field = (k: string) => fm.match(new RegExp(`^${k}:\\s*(.*)$`, "m"))?.[1]?.trim();
  const globs = (field("globs") ?? "").split(",").map((g) => g.trim()).filter(Boolean);
  return { name, description: field("description"), globs, alwaysApply: field("alwaysApply") === "true" };
}

export function mode(r: Rule): Mode {
  if (r.alwaysApply) return "always";
  if (r.globs.length) return "auto-attached";
  return r.description ? "agent-requested" : "manual";
}

export function loadRules(repo: string): Rule[] {
  const dir = join(repo, ".cursor", "rules");
  return readdirSync(dir, { recursive: true, encoding: "utf8" })
    .filter((f) => f.endsWith(".mdc"))
    .sort()
    .map((f) => parseMdc(f.replace(/\.mdc$/, ""), readFileSync(join(dir, f), "utf8")));
}

export function included(rules: Rule[], files: string[]): string[] {
  return rules
    .filter((r) => mode(r) === "always" || (mode(r) === "auto-attached" && r.globs.some((g) => files.some((f) => globToRegExp(g).test(f)))))
    .map((r) => r.name);
}
