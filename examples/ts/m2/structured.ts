// L2.3: structured output validated by a Zod schema (the SDK validates for you).
import { generateText, Output } from "ai";
import { z } from "zod";
import { getModel, scriptedModel, text } from "../lib/mock.ts";

export const Event = z.object({ title: z.string(), date: z.string(), location: z.string() });

export async function extractEvent(input: string, reply?: string) {
  const mock = scriptedModel(() => [
    text(reply ?? '{"title":"Rust meetup","date":"2026-11-20","location":"Bengaluru"}'),
  ]);
  const { output } = await generateText({
    model: await getModel(mock),
    prompt: input,
    output: Output.object({ schema: Event }),
  });
  return output;
}
