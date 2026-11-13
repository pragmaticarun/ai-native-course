import { Command } from "@langchain/langgraph";
import { expect, test } from "vitest";
import { mapLimit } from "./fanout.ts";
import { buildTriage } from "./triage.ts";

test("complete invoice is filed automatically", async () => {
  const g = buildTriage();
  const out = await g.invoke({ text: "Invoice 9: USD 1,200.00 due 2026-12-01." }, { configurable: { thread_id: "a" } });
  expect(out.decision).toBe("auto");
  expect(out.filed).toBe("invoice:amount=USD 1,200.00,due_date=2026-12-01");
});

test("missing field interrupts, then resumes with the human's answer", async () => {
  const g = buildTriage();
  const cfg = { configurable: { thread_id: "b" } };
  const paused = await g.invoke({ text: "App crash on Galaxy A73, no version given." }, cfg);
  // invoke() returns the paused state plus `__interrupt__` (not part of the declared state type)
  const pending = (paused as { __interrupt__?: { value: unknown }[] }).__interrupt__;
  expect(pending?.[0].value).toEqual({ kind: "bug_report", issues: ["missing version"] });
  const out = await g.invoke(new Command({ resume: "approve" }), cfg);
  expect(out.decision).toBe("approve");
  expect(out.filed).toContain("device=Galaxy A73");
});

test("mapLimit bounds concurrency, keeps order and collects failures", async () => {
  let active = 0;
  let peak = 0;
  const out = await mapLimit([1, 2, 3, 4, 5, 6], 2, async (n) => {
    active++;
    peak = Math.max(peak, active);
    await new Promise((r) => setTimeout(r, 5));
    active--;
    if (n === 4) throw new Error("ocr failed on 4");
    return n * 10;
  });
  expect(peak).toBe(2);
  expect(out.map((r) => (r.ok ? r.value : r.error))).toEqual([10, 20, 30, "ocr failed on 4", 50, 60]);
});
