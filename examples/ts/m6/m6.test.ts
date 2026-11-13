import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, test } from "vitest";
import { atMostCalls, callsFirst, contains, grade, runCase } from "./evals.ts";

const repo = () => {
  const root = mkdtempSync(join(tmpdir(), "m6-"));
  mkdirSync(join(root, "src"));
  writeFileSync(join(root, "src", "app.py"), "def main():\n    print('hi')\n");
  return root;
};

test("trajectory + answer graders pass on the explorer", async () => {
  const r = await runCase(repo(), "Where is the entry point?");
  expect(r.trajectory).toEqual(["grep"]);
  expect(grade(r.answer, r.trajectory, [callsFirst("grep"), atMostCalls(3), contains("src/app.py")])).toEqual([]);
});

test("graders report failures", () => {
  expect(grade("nothing", ["read_file"], [callsFirst("grep"), contains("app.py")])).toHaveLength(2);
});

test("token budget stops the run after the first step", async () => {
  const r = await runCase(repo(), "Where is the entry point?", 1); // mock usage is 15 tokens per step
  expect(r.steps).toBe(1);
  expect(r.answer).toBe("");
  expect(r.tokens).toBe(15);
});
