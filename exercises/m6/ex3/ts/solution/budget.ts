import { generateText, isStepCount, type LanguageModel, type StepResult, type ToolSet } from "ai";

export type Price = { inputPerMTok: number; outputPerMTok: number };
export type BudgetArgs = { model: LanguageModel; tools: ToolSet; prompt: string; maxUsd: number; price: Price; maxSteps?: number };

const spent = (steps: Array<StepResult<ToolSet>>, p: Price) =>
  steps.reduce((usd, s) => usd + ((s.usage.inputTokens ?? 0) * p.inputPerMTok + (s.usage.outputTokens ?? 0) * p.outputPerMTok) / 1e6, 0);

export async function runWithBudget({ model, tools, prompt, maxUsd, price, maxSteps = 20 }: BudgetArgs) {
  let budgetHit = false;
  const result = await generateText({
    model,
    tools,
    prompt,
    stopWhen: [
      isStepCount(maxSteps),
      ({ steps }) => (budgetHit = spent(steps, price) >= maxUsd),
    ],
  });
  const last = result.steps.at(-1);
  const answered = !!last && last.toolCalls.length === 0;
  return {
    text: result.text,
    stoppedBy: answered ? "answer" : budgetHit ? "budget" : "steps",
    spentUsd: spent(result.steps, price),
    steps: result.steps.length,
  };
}
