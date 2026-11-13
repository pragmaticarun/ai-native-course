export type ToolCall = { id: string; name: string; args: Record<string, unknown> };
export type Msg = { role: "user" | "assistant" | "tool"; content: string; toolCalls?: ToolCall[]; toolCallId?: string };
export type Turn = { text: string; toolCalls: ToolCall[] };
export interface Model { complete(messages: Msg[]): Promise<Turn> }
export type Tools = Record<string, (args: Record<string, unknown>) => unknown | Promise<unknown>>;
export type RunResult = { answer: string | null; stopReason: "answered" | "max_steps"; steps: number };

export async function runAgent(model: Model, tools: Tools, task: string, maxSteps = 8): Promise<RunResult> {
  // TODO: port scratch_loop.py
  void model; void tools; void task;
  return { answer: null, stopReason: "max_steps", steps: maxSteps };
}
