// M6 in TypeScript: trajectory graders over AI SDK steps, and a token budget as a stop condition.
import { generateText, isStepCount, type StopCondition, type ToolSet } from "ai";
import { makeTools, mockExplorer } from "../m3/explorer.ts";
import { getModel } from "../lib/mock.ts";

export type Grader = (answer: string, trajectory: string[]) => string | null;

export const callsFirst = (tool: string): Grader => (_a, t) => (t[0] === tool ? null : `first call should be ${tool}, got ${t[0]}`);
export const atMostCalls = (n: number): Grader => (_a, t) => (t.length <= n ? null : `${t.length} calls > ${n}`);
export const contains = (needle: string): Grader => (a) => (a.includes(needle) ? null : `missing ${JSON.stringify(needle)}`);

/** Stop once the run has used `maxTokens` (input + output) across all steps. */
export function tokenBudget<T extends ToolSet>(maxTokens: number): StopCondition<T> {
  return ({ steps }) => steps.reduce((sum, s) => sum + (s.usage.inputTokens ?? 0) + (s.usage.outputTokens ?? 0), 0) >= maxTokens;
}

export async function runCase(root: string, question: string, maxTokens = 10_000) {
  const result = await generateText({
    model: await getModel(mockExplorer()),
    system: "You explore a codebase with read-only tools.",
    prompt: question,
    tools: makeTools(root),
    stopWhen: [isStepCount(6), tokenBudget(maxTokens)],
  });
  const trajectory = result.steps.flatMap((s) => s.toolCalls.map((c) => c.toolName));
  const tokens = result.steps.reduce((n, s) => n + (s.usage.inputTokens ?? 0) + (s.usage.outputTokens ?? 0), 0);
  return { answer: result.text, trajectory, tokens, steps: result.steps.length };
}

export function grade(answer: string, trajectory: string[], graders: Grader[]): string[] {
  return graders.map((g) => g(answer, trajectory)).filter((p): p is string => p !== null);
}
