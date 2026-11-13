// L5.4 in TypeScript: the AI SDK pauses a destructive tool call until a human answers.
// `toolApproval: { delete_recording: "user-approval" }` makes generateText stop with a
// `tool-approval-request`; we resume by sending a `tool-approval-response` message.
import { generateText, tool, type ModelMessage } from "ai";
import { z } from "zod";
import { getModel, scriptedModel, text, toolCall } from "../lib/mock.ts";

export function makeTools(deleted: string[]) {
  return {
    delete_recording: tool({
      description: "Delete a recording permanently.",
      inputSchema: z.object({ name: z.string() }),
      execute: async ({ name }) => {
        deleted.push(name);
        return `deleted ${name}`;
      },
    }),
  };
}

type Part = { type: string; output?: { type?: string; value?: unknown; reason?: string } };

export const mockAgent = () =>
  scriptedModel((prompt) => {
    const toolMsgs = (prompt as Array<{ role: string; content: Part[] }>).filter((m) => m.role === "tool");
    const results = toolMsgs.flatMap((m) => m.content).filter((p) => p.type === "tool-result");
    if (results.length === 0) return [toolCall("delete_recording", { name: "meeting.m4a" })];
    const out = results[0].output;
    return [text(out?.type === "execution-denied" ? `Not deleted: ${out.reason ?? "denied"}` : `Done: ${String(out?.value)}`)];
  });

export async function runWithApproval(decide: (call: { toolName: string; input: unknown }) => { approved: boolean; reason: string }) {
  const deleted: string[] = [];
  const tools = makeTools(deleted);
  const model = await getModel(mockAgent());
  const messages: ModelMessage[] = [{ role: "user", content: "Delete the meeting recording." }];
  const first = await generateText({ model, tools, messages, toolApproval: { delete_recording: "user-approval" } });
  const requests = first.content.filter((p) => p.type === "tool-approval-request");
  messages.push(...first.response.messages);
  messages.push({
    role: "tool",
    content: requests.map((r) => ({ type: "tool-approval-response" as const, approvalId: r.approvalId, ...decide(r.toolCall) })),
  });
  const second = await generateText({ model, tools, messages, toolApproval: { delete_recording: "user-approval" } });
  return { pausedFor: requests.map((r) => r.toolCall.toolName), deleted, text: second.text };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  console.log(await runWithApproval(() => ({ approved: false, reason: "keep for the minutes" })));
  console.log(await runWithApproval(() => ({ approved: true, reason: "duplicate of the upload" })));
}
