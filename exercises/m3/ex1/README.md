# M3 · Exercise 1 — Add reflection after failed tool calls

Copy the loop idea from `scratch_loop.py` and implement
`run_with_reflection(model, tools, task, max_steps=8)` returning `(answer, reflections)`:

- run tool calls as usual (errors become observations starting with `"error:"`);
- after a step in which **any** tool result starts with `"error:"`, append one extra user
  message beginning with `"Reflect:"` that quotes the failing call name and asks the model
  to change approach before its next action; count it;
- return `(final_text, number_of_reflections)`, or `(None, n)` if the step budget runs out.

`tools` maps a name to a plain Python function.
