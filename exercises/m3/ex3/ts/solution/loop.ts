export type ToolCall = { id: string; name: string; args: Record<string, unknown> };
export type Msg = { role: "user" | "assistant" | "tool"; content: string; toolCalls?: ToolCall[]; toolCallId?: string };
export type Turn = { text: string; toolCalls: ToolCall[] };
export interface Model { complete(messages: Msg[]): Promise<Turn> }
export type Tools = Record<string, (args: Record<string, unknown>) => unknown | Promise<unknown>>;
export type RunResult = { answer: string | null; stopReason: "answered" | "max_steps"; steps: number };

async function execute(tools: Tools, call: ToolCall): Promise<string> {
  const fn = tools[call.name];
  if (!fn) return `error: no tool named ${call.name}; available: ${Object.keys(tools).sort().join(", ")}`;
  try {
    return String(await fn(call.args));
  } catch (err) {
    return `error: ${(err as Error).message}`;
  }
}

export async function runAgent(model: Model, tools: Tools, task: string, maxSteps = 8): Promise<RunResult> {
  const messages: Msg[] = [{ role: "user", content: task }];
  for (let step = 1; step <= maxSteps; step++) {
    const turn = await model.complete(messages);
    if (turn.toolCalls.length === 0) return { answer: turn.text, stopReason: "answered", steps: step };
    messages.push({ role: "assistant", content: turn.text, toolCalls: turn.toolCalls });
    for (const call of turn.toolCalls) {
      messages.push({ role: "tool", content: await execute(tools, call), toolCallId: call.id });
    }
  }
  return { answer: null, stopReason: "max_steps", steps: maxSteps };
}
