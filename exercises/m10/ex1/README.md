# Ex 10.1: a spec that is its own test oracle

The `clip-encode` CLI should accept bitrates like `2.5M` instead of raw bits per second. The team agreed:

- a bare whole number is bits per second (`800000` → 800000);
- `k` means ×1,000 and `M` means ×1,000,000 (decimal, not 1024); lowercase `m` is **rejected** (milli? mega?);
- a decimal is allowed before a unit if the result is a whole number (`2.5M` → 2500000), otherwise rejected (`1.0005k`);
- empty input and negative numbers are rejected.

`starter/spec.md` is the draft an agent wrote from a one-line request: it has open clarifications, a vague success
criterion, no out-of-scope line and not enough examples. Rewrite it in Spec Kit's format so that:

1. `speckit.lint_spec` reports nothing;
2. its acceptance scenarios, read with `speckit.examples_from_spec` (one backticked value in the Given, one in the
   Then, `error` for "rejected"), pass against the reference implementation;
3. and every one of four plausible-but-wrong implementations fails at least one of your scenarios. The tests
   don't tell you what the mutants get wrong; the rules above do.

This is the same loop you'd run with `/speckit-specify` then `/speckit-clarify`: the agent drafts, you make it precise.
