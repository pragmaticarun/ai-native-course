# Ex 13.4: migrate a MediaPipe `LlmInference` sample to LiteRT-LM (reading exercise, untested)

MediaPipe's LLM Inference API (`com.google.mediapipe:tasks-genai`, `LlmInference`) is deprecated in
favour of LiteRT-LM (`com.google.ai.edge.litertlm:litertlm-android`, `Engine` / `Conversation`).
This exercise needs the Android SDK and a device, so it has **no automated tests here and has not
been run** (the course box deliberately has no Android SDK).

Do it on your machine:

1. Start from a sample that creates `LlmInference` from options (model path, max tokens) and calls
   `generateResponse` / `generateResponseAsync`.
2. Replace it with a LiteRT-LM `Engine` created **off the main thread** (the LiteRT-LM docs say so),
   a `Conversation` per chat, and a `Flow` of tokens collected in a `ViewModel` scope.
3. Swap the `.task` model for a `.litertlm` model from the A73 ladder (FunctionGemma 270M first,
   then Gemma 3 1B). CPU backend first; try GPU only after CPU works.
4. Put the engine behind the `LocalModel` interface in `kmp/shared/.../m13/VoiceNotes.kt` so the
   commonMain tests keep passing with the scripted model.
5. Record TTFT, tokens/s and peak RSS on the A73 for both versions.

Check every API name against the current LiteRT-LM Android guide
(https://developers.google.com/edge/litert-lm/android) and the MediaPipe deprecation note
(https://developers.google.com/edge/mediapipe/solutions/genai/llm_inference) before you start.
