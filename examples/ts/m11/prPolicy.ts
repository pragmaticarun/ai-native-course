// M11 L11.4: the agent-PR review policy from review.py, in TypeScript (for a GitHub
// Action or a bot). The conventions (agent-authored label / Agent-Session trailer,
// 400 changed lines, two reviewers for migrations and workflows) are this course's.
import { globToRegExp } from "../m10/rules.ts";

export interface PR {
  author: string;
  requestedBy?: string;
  labels: string[];
  commits: string[];
  files: Record<string, [added: number, removed: number]>;
}

export const GENERATED = ["**/*.lock", "**/pnpm-lock.yaml", "**/package-lock.json", "**/uv.lock", "**/*_pb2.py", "**/dist/**"];

export function provenance(pr: PR): "agent" | "human" {
  const trailer = pr.commits.some((c) => /^Agent-Session: \S+/m.test(c));
  return pr.labels.includes("agent-authored") || trailer ? "agent" : "human";
}

export function size(pr: PR): number {
  const gen = GENERATED.map(globToRegExp);
  return Object.entries(pr.files)
    .filter(([path]) => !gen.some((g) => g.test(path)))
    .reduce((n, [, [a, r]]) => n + a + r, 0);
}

export interface Decision { provenance: "agent" | "human"; size: number; blockers: string[]; reviewersNeeded: number; notSoleApprover: string[] }

export function decide(pr: PR, limit = 400): Decision {
  const d: Decision = { provenance: provenance(pr), size: size(pr), blockers: [], reviewersNeeded: 1, notSoleApprover: [] };
  if (d.size > limit) d.blockers.push(`${d.size} changed lines > ${limit}: split into stacked PRs`);
  if (d.provenance === "agent") {
    if (pr.requestedBy) d.notSoleApprover.push(pr.requestedBy);
    if (Object.keys(pr.files).some((p) => p.startsWith("migrations/") || p.startsWith(".github/workflows/"))) d.reviewersNeeded = 2;
  }
  return d;
}

/** Can this set of approvals merge? Requester alone never counts for an agent PR. */
export function canMerge(d: Decision, approvers: string[]): boolean {
  const counted = new Set(approvers);
  if (counted.size === 1 && d.notSoleApprover.some((p) => counted.has(p))) return false;
  return d.blockers.length === 0 && counted.size >= d.reviewersNeeded;
}
