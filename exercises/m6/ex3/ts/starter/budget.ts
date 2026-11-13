import type { LanguageModel, ToolSet } from "ai";

export type Price = { inputPerMTok: number; outputPerMTok: number };
export type BudgetArgs = { model: LanguageModel; tools: ToolSet; prompt: string; maxUsd: number; price: Price; maxSteps?: number };

export async function runWithBudget(args: BudgetArgs): Promise<{ text: string; stoppedBy: string; spentUsd: number; steps: number }> {
  // TODO
  throw new Error("not implemented");
}
