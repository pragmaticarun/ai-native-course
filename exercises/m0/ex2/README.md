# M0 · Exercise 2 — Make the mock model return a scripted tool call

Write `make_scripted_model()` returning an `aincourse.ScriptedModel` that:

1. on the first call, asks for the tool `get_time` with arguments `{"tz": "Asia/Kolkata"}`;
2. on the next call, answers in text: `"It is <tool result> in Kolkata."`, using the
   tool result it was given (don't hard-code the time).

The test drives it with a tiny loop that runs the tool and sends the result back.
