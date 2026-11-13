import type { ModelMessage } from "ai";
import { describe, expect, it } from "vitest";
import { approxTokens, compact, fitHistory, mockSummariser, pinnedLines } from "./context.ts";

describe("M4 context (TS)", () => {
  const convo: ModelMessage[] = [{ role: "system", content: "sys" }];
  for (let i = 0; i < 10; i++) convo.push({ role: "user", content: `turn ${i} ${"x".repeat(200)}` });
  convo.splice(3, 0, { role: "user", content: "CONSTRAINT: must run on a Galaxy A73 CPU." });

  it("compacts old turns, keeps the system prompt, last turns and pins", async () => {
    const out = await compact(convo, mockSummariser(), 3);
    expect(out[0]).toEqual(convo[0]);
    expect(out.slice(-3)).toEqual(convo.slice(-3));
    expect(out).toHaveLength(5);
    expect(String(out[1].content)).toContain("CONSTRAINT: must run on a Galaxy A73 CPU.");
    expect(pinnedLines(convo)).toHaveLength(1);
  });

  it("leaves short conversations alone", async () => {
    expect(await compact(convo.slice(0, 3), mockSummariser(), 4)).toEqual(convo.slice(0, 3));
  });

  it("fits newest history under the budget", () => {
    const history = Array.from({ length: 50 }, (_, i) => `turn ${i} ${"y".repeat(100)}`);
    const r = fitHistory("instructions", history, 500);
    expect(r.tokens).toBeLessThanOrEqual(500);
    expect(r.prompt).toContain("turn 49");
    expect(r.prompt).not.toContain("turn 0 ");
    expect(approxTokens(r.prompt)).toBeLessThanOrEqual(510);
    expect(() => fitHistory("z".repeat(4000), [], 10)).toThrow();
  });
});
