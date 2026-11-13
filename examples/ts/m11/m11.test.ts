import { expect, test } from "vitest";
import { canMerge, decide, type PR } from "./prPolicy.ts";

const base: PR = { author: "bot", requestedBy: "asha", labels: [], commits: ["fix: clamp end\n\nAgent-Session: mock-1"], files: { "src/clip.py": [12, 3], "tests/test_clip.py": [20, 0] } };

test("provenance from the trailer, and the requester can't approve alone", () => {
  const d = decide(base);
  expect(d).toMatchObject({ provenance: "agent", size: 35, blockers: [], reviewersNeeded: 1, notSoleApprover: ["asha"] });
  expect(canMerge(d, ["asha"])).toBe(false);
  expect(canMerge(d, ["ben"])).toBe(true);
  expect(canMerge(d, ["asha", "ben"])).toBe(true);
});

test("size excludes generated files; oversized PRs are blocked", () => {
  const big: PR = { ...base, files: { "src/a.py": [300, 150], "uv.lock": [4000, 3000], "web/dist/app.js": [9000, 0] } };
  const d = decide(big);
  expect(d.size).toBe(450);
  expect(d.blockers).toEqual(["450 changed lines > 400: split into stacked PRs"]);
  expect(canMerge(d, ["ben", "chen"])).toBe(false);
});

test("migrations and workflows need two reviewers; human PRs don't get agent rules", () => {
  const mig = decide({ ...base, labels: ["agent-authored"], commits: [], files: { "migrations/0007.py": [30, 0] } });
  expect(mig.reviewersNeeded).toBe(2);
  expect(canMerge(mig, ["ben"])).toBe(false);
  const human = decide({ ...base, commits: ["fix"], files: { ".github/workflows/ci.yml": [3, 1] } });
  expect(human).toMatchObject({ provenance: "human", reviewersNeeded: 1, notSoleApprover: [] });
});
