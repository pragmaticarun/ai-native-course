# M2 · Exercise 1 — Repair loop for tool arguments that fail validation

Implement `convert_with_repair(model, question, max_attempts=3)`:

- Send the question with the `CONVERT` tool spec (provided).
- When the model calls `convert`, validate the arguments with the `ConvertArgs` Pydantic
  model. On `ValidationError`, send the error text back as the **tool result** (role
  `"tool"`, same `tool_call_id`) starting with `"error:"` and let the model try again.
- On valid arguments, run `convert()` and send the result back; return the model's final text.
- Raise `RuntimeError` if the model still hasn't produced valid arguments after
  `max_attempts` tool calls.
