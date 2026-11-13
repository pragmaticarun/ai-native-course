# Ex 13.3: a router that keeps PII on the device

Write `route(prompt, sensitive, online, local_ok, local_ctx, est_tokens, hard)` returning
`"local"`, `"cloud"` or `"refuse"`:

1. A prompt with PII (an email address, a phone number of 10+ digits possibly with spaces, dashes or a
   leading `+`, or a 13-19 digit card number) or `sensitive=True` **must not** go to the cloud. Use
   local if the local model is available and the prompt fits (`est_tokens <= local_ctx`); otherwise
   `"refuse"` (ask the user; never "fall back" to the cloud with private data).
2. Otherwise: offline means local if it fits, else refuse.
3. Otherwise: cloud if the local model is unavailable, the prompt doesn't fit, or the task is `hard`.
4. Otherwise local.

Also write `has_pii(text) -> bool`. Reference: `examples/python/m13/privacy_router.py`.
