# M3 · Exercise 3 — Port the scratch loop to TypeScript

Implement `runAgent(model, tools, task, maxSteps = 8)` in `loop.ts`, mirroring
`examples/python/m3/scratch_loop.py` (no framework):

- `model.complete(messages)` returns `{ text, toolCalls }`;
- execute every tool call; unknown tools and thrown errors become observations
  starting with `"error:"` (never crash the loop);
- stop with `{ answer, stopReason: "answered", steps }` when there are no tool calls, or
  `{ answer: null, stopReason: "max_steps", steps: maxSteps }` when the budget runs out.
