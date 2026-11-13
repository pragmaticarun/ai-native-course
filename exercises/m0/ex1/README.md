# M0 · Exercise 1 — Switch providers with environment variables only

Implement `resolve_provider(env)` so that the provider and model come **only** from
environment variables, never from code:

- `COURSE_LLM_PROVIDER` missing or empty → `ProviderConfig("mock", None, None)`.
- `openai` / `anthropic` (any case, surrounding spaces ignored) → needs `COURSE_LLM_MODEL`
  and that provider's key variable (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`) to be non-empty.
  Return `ProviderConfig(provider, model, key_var)`.
- Anything else, or a missing model/key → raise `ValueError` with a helpful message.

Never return or print the key itself, only the *name* of the variable.
