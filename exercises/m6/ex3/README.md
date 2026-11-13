# M6 · Exercise 3 (TypeScript) — A per-run cost budget that aborts gracefully

Implement `runWithBudget({ model, tools, prompt, maxUsd, price, maxSteps })` in `budget.ts`
with the AI SDK's `generateText`:

- `price` is `{ inputPerMTok, outputPerMTok }` in USD;
- add a custom `stopWhen` condition that stops once the run's total cost (sum over steps of
  `usage.inputTokens`/`usage.outputTokens` × price) reaches `maxUsd`, alongside
  `isStepCount(maxSteps)`;
- return `{ text, stoppedBy, spentUsd, steps }` where `stoppedBy` is `"answer"` if the last
  step finished without tool calls, `"budget"` if the cost condition fired, otherwise `"steps"`.
- never throw because of the budget: a budget stop is a normal, reportable outcome.
