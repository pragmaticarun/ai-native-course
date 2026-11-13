# M2 · Exercise 2 — Measure tokens per call

Implement `TokenMeter` with:

- `record(turn: AssistantTurn)` — store the turn's `input_tokens`/`output_tokens`;
- `total` → `(input, output)` tuple; `calls` → number of recorded turns;
- `mean_per_call()` → `(input, output)` floats (`(0.0, 0.0)` when empty);
- `most_expensive(input_weight=1.0, output_weight=4.0)` → index of the call with the
  highest weighted cost (first one wins ties), or `None` when empty.

Then use it in a loop to see how the input grows with every step (the conversation is
resent each time).
