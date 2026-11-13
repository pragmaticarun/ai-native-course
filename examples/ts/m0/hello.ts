// M0 worked example: hello, mock first. Run: pnpm tsx examples/ts/m0/hello.ts
import { generateText } from "ai";
import { getModel, scriptedModel, text } from "../lib/mock.ts";

export async function hello(name: string): Promise<string> {
  const model = await getModel(
    scriptedModel(() => [text(`Hello, ${name}! (mock model, no network used)`)]),
  );
  const { text: reply } = await generateText({
    model,
    system: "You are a terse assistant for systems engineers.",
    prompt: `Say hello to ${name}.`,
  });
  return reply;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  console.log(await hello(process.argv[2] ?? "Arunkumar"));
}
