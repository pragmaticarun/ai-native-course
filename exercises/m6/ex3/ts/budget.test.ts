import { tool } from "ai";
import { expect, test } from "vitest";
import { z } from "zod";
import { scriptedModel, text, toolCall } from "../../../../examples/ts/lib/mock.ts";

const variant = process.env.EXERCISE_VARIANT ?? "solution";
const { runWithBudget } = (await import(`./${variant}/budget.ts`)) as typeof import("./solution/budget.ts");

const tools = { ping: tool({ description: "ping", inputSchema: z.object({}), execute: async () => "pong" }) };
const forever = () => scriptedModel(() => [toolCall("ping", {})]); // never answers
const price = { inputPerMTok: 1_000_000, outputPerMTok: 1_000_000 }; // $1 per token: easy maths (mock usage = 15 tokens/step)

test("stops at the budget, gracefully", async () => {
  const r = await runWithBudget({ model: forever(), tools, prompt: "go", maxUsd: 40, price, maxSteps: 10 });
  expect(r).toEqual({ text: "", stoppedBy: "budget", spentUsd: 45, steps: 3 });
});

test("step limit when the budget is large", async () => {
  const r = await runWithBudget({ model: forever(), tools, prompt: "go", maxUsd: 1e9, price, maxSteps: 2 });
  expect(r.stoppedBy).toBe("steps");
  expect(r.steps).toBe(2);
});

test("answer before budget", async () => {
  const r = await runWithBudget({ model: scriptedModel(() => [text("hi")]), tools, prompt: "go", maxUsd: 100, price });
  expect(r).toEqual({ text: "hi", stoppedBy: "answer", spentUsd: 15, steps: 1 });
});
