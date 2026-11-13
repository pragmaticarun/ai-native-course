// M4 in TypeScript: compaction with an AI SDK summariser, plus a budgeted prompt builder.
import { generateText, type LanguageModel, type ModelMessage } from "ai";
import { getModel, scriptedModel, text } from "../lib/mock.ts";

export const approxTokens = (s: string) => Math.ceil(s.length / 4);
const PINS = ["DECISION:", "CONSTRAINT:", "FACT:"];

const contentOf = (m: ModelMessage) => (typeof m.content === "string" ? m.content : JSON.stringify(m.content));

export function pinnedLines(messages: ModelMessage[]): string[] {
  return messages.flatMap((m) =>
    contentOf(m).split("\n").map((l) => l.trim()).filter((l) => PINS.some((p) => l.startsWith(p))),
  );
}

/** Keep system + last `keepLast` messages; summarise the rest; copy pinned lines verbatim. */
export async function compact(messages: ModelMessage[], model: LanguageModel, keepLast = 4): Promise<ModelMessage[]> {
  const system = messages.filter((m) => m.role === "system");
  const rest = messages.filter((m) => m.role !== "system");
  if (rest.length <= keepLast) return messages;
  const old = rest.slice(0, -keepLast);
  const { text: summary } = await generateText({
    model,
    system: "Summarise this conversation in under 80 words.",
    prompt: old.map((m) => `${m.role}: ${contentOf(m)}`).join("\n"),
  });
  const pins = pinnedLines(old);
  const body = `Summary of earlier conversation: ${summary.trim()}` + (pins.length ? `\nPinned (verbatim):\n${pins.join("\n")}` : "");
  return [...system, { role: "user", content: body }, ...rest.slice(-keepLast)];
}

/** Newest history first until the budget is used; instructions are never dropped. */
export function fitHistory(instructions: string, history: string[], budget: number) {
  let used = approxTokens(instructions);
  if (used > budget) throw new Error("instructions alone exceed the budget");
  const kept: string[] = [];
  for (const turn of [...history].reverse()) {
    if (used + approxTokens(turn) > budget) break;
    kept.unshift(turn);
    used += approxTokens(turn);
  }
  return { prompt: [instructions, ...kept].join("\n\n"), tokens: used, dropped: history.length - kept.length };
}

export const mockSummariser = () => scriptedModel(() => [text("We discussed the pipeline design.")]);

if (import.meta.url === `file://${process.argv[1]}`) {
  const convo: ModelMessage[] = [{ role: "system", content: "You help plan a media pipeline." }];
  for (let i = 0; i < 12; i++) convo.push({ role: "user", content: `Turn ${i}: ${"chatter ".repeat(30)}` });
  convo.splice(2, 0, { role: "user", content: "DECISION: output is 48 kHz stereo AAC." });
  const short = await compact(convo, await getModel(mockSummariser()));
  console.log(short.length, "messages;", contentOf(short[1]));
}
