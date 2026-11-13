import { expect, test } from "vitest";
import type { Model, Msg, Turn } from "./solution/loop.ts";

const variant = process.env.EXERCISE_VARIANT ?? "solution";
const { runAgent } = (await import(`./${variant}/loop.ts`)) as typeof import("./solution/loop.ts");

const scripted = (decide: (m: Msg[]) => Turn): Model & { seen: Msg[][] } => {
  const seen: Msg[][] = [];
  return { seen, complete: async (m) => (seen.push([...m]), decide(m)) };
};

test("answers after one tool call", async () => {
  const model = scripted((m) => {
    const last = m.at(-1)!;
    return last.role === "tool"
      ? { text: `sum is ${last.content}`, toolCalls: [] }
      : { text: "", toolCalls: [{ id: "c1", name: "add", args: { a: 2, b: 3 } }] };
  });
  const tools = { add: (a: Record<string, unknown>) => Number(a.a) + Number(a.b) };
  expect(await runAgent(model, tools, "2+3?")).toEqual({ answer: "sum is 5", stopReason: "answered", steps: 2 });
});

test("errors and unknown tools are observations", async () => {
  const model = scripted((m) =>
    m.filter((x) => x.role === "tool").length >= 2
      ? { text: m.filter((x) => x.role === "tool").map((x) => x.content).join(" | "), toolCalls: [] }
      : { text: "", toolCalls: [{ id: "c", name: m.length === 1 ? "boom" : "ghost", args: {} }] },
  );
  const tools = { boom: () => { throw new Error("kaput"); } };
  const r = await runAgent(model, tools, "x");
  expect(r.stopReason).toBe("answered");
  expect(r.answer).toBe("error: kaput | error: no tool named ghost; available: boom");
});

test("step budget", async () => {
  const model = scripted(() => ({ text: "", toolCalls: [{ id: "c", name: "noop", args: {} }] }));
  expect(await runAgent(model, { noop: () => "ok" }, "x", 3)).toEqual({ answer: null, stopReason: "max_steps", steps: 3 });
});
