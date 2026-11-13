import { isAbsolute, normalize } from "node:path";

const VALUE_OPTS = new Set(["-i", "-ss", "-t", "-to", "-vf", "-af", "-c:v", "-c:a", "-b:a", "-ar", "-ac", "-frames:v"]);
const FLAG_OPTS = new Set(["-an", "-vn", "-y"]);
const BAD_FILTERS = ["movie", "amovie", "sendcmd", "asendcmd", "zmq", "azmq"];

function checkPath(p: string): string | null {
  if (/^[A-Za-z][A-Za-z0-9+.-]*:/.test(p)) return `protocol not allowed: ${p}`;
  const n = normalize(p);
  if (isAbsolute(p) || n === ".." || n.startsWith("../")) return `path escapes root: ${p}`;
  return null;
}

export function checkArgs(args: string[], root: string): string[] {
  void root; // paths are checked relative to it: relative, normalised, no escape
  const problems: string[] = [];
  if (args.length === 0) return ["no output"];
  const body = args.slice(0, -1);
  for (let i = 0; i < body.length; i++) {
    const a = body[i];
    if (FLAG_OPTS.has(a)) continue;
    if (!VALUE_OPTS.has(a)) {
      problems.push(`option not allowed: ${a}`);
      continue;
    }
    const v = body[++i] ?? "";
    if (a === "-i") {
      const p = checkPath(v);
      if (p) problems.push(p);
    }
    if (a === "-vf" || a === "-af") {
      for (const f of BAD_FILTERS) {
        if (new RegExp(`(^|[,;\\[\\]])\\s*${f}\\s*(=|$|[,;])`).test(v)) problems.push(`filter not allowed: ${f}`);
      }
    }
  }
  const out = checkPath(args[args.length - 1]);
  if (out) problems.push(out);
  return problems;
}
