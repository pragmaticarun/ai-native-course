// Helpers for deterministic, offline examples built on the AI SDK's MockLanguageModelV4.
import type { LanguageModel } from "ai";
import { MockLanguageModelV4 } from "ai/test";

const usage = {
  inputTokens: { total: 10, noCache: 10, cacheRead: 0, cacheWrite: 0 },
  outputTokens: { total: 5, text: 5, reasoning: 0 },
};

export type MockContent =
  | { type: "text"; text: string }
  | { type: "tool-call"; toolCallId: string; toolName: string; input: string };

export const text = (t: string): MockContent => ({ type: "text", text: t });
export const toolCall = (toolName: string, input: unknown, toolCallId = "call_1"): MockContent => ({
  type: "tool-call",
  toolCallId,
  toolName,
  input: JSON.stringify(input),
});

/** A mock model whose `decide` function sees the prompt and returns content. */
export function scriptedModel(decide: (prompt: unknown[], call: number) => MockContent[]) {
  let calls = 0;
  return new MockLanguageModelV4({
    doGenerate: async (options) => {
      calls += 1;
      const content = decide(options.prompt as unknown[], calls);
      const hasTool = content.some((c) => c.type === "tool-call");
      return {
        content,
        finishReason: { unified: hasTool ? "tool-calls" : "stop", raw: undefined },
        usage,
        warnings: [],
      };
    },
  });
}

/**
 * Provider-agnostic model selection: COURSE_LLM_PROVIDER=mock|openai|anthropic,
 * COURSE_LLM_MODEL=<model id>. Live providers are optional packages
 * (`pnpm add @ai-sdk/openai` or `@ai-sdk/anthropic`) and are NOT tested in CI.
 */
export async function getModel(mock: LanguageModel): Promise<LanguageModel> {
  const provider = (process.env.COURSE_LLM_PROVIDER ?? "mock").toLowerCase();
  if (provider === "mock") return mock;
  const modelId = process.env.COURSE_LLM_MODEL;
  if (!modelId) throw new Error("Set COURSE_LLM_MODEL to your provider's model id for live mode.");
  const pkg = { openai: "@ai-sdk/openai", anthropic: "@ai-sdk/anthropic" }[provider];
  if (!pkg) throw new Error(`Unknown COURSE_LLM_PROVIDER=${provider}`);
  const mod = (await import(pkg as string)) as Record<string, (id: string) => LanguageModel>;
  return mod[provider](modelId);
}
