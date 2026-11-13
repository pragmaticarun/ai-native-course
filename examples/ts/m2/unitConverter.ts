// L2.4: tool calling with the AI SDK. The mock model calls `convert`, then phrases the result.
import { generateText, isStepCount, tool } from "ai";
import { z } from "zod";
import { getModel, scriptedModel, text, toolCall } from "../lib/mock.ts";

const FACTORS: Record<string, number> = { "km>mi": 0.621371, "mi>km": 1.609344, "kg>lb": 2.204623, "lb>kg": 0.453592 };

export function convert(value: number, fromUnit: string, toUnit: string): number {
  const f = FACTORS[`${fromUnit}>${toUnit}`];
  if (f === undefined) throw new Error(`unsupported conversion ${fromUnit}->${toUnit}`);
  return Math.round(value * f * 10_000) / 10_000;
}

export const tools = {
  convert: tool({
    description: "Convert a value between units. Supported: km<->mi, kg<->lb.",
    inputSchema: z.object({ value: z.number(), fromUnit: z.string(), toUnit: z.string() }),
    execute: async ({ value, fromUnit, toUnit }) => convert(value, fromUnit, toUnit),
  }),
};

export const mockBrain = () =>
  scriptedModel((prompt) => {
    const last = prompt.at(-1) as { role: string; content: Array<{ output?: { value?: unknown } }> };
    if (last.role === "tool") return [text(`That is ${String(last.content[0]?.output?.value)} miles.`)];
    return [toolCall("convert", { value: 42.195, fromUnit: "km", toUnit: "mi" })];
  });

export async function ask(question: string) {
  const result = await generateText({
    model: await getModel(mockBrain()),
    system: "Use the convert tool for unit conversions.",
    prompt: question,
    tools,
    stopWhen: isStepCount(5),
  });
  return { text: result.text, steps: result.steps.length };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  console.log((await ask("How many miles is a marathon?")).text);
}
