package course.m2

/**
 * Deterministic stand-ins for the two backends described in SYLLABUS.md v0.3:
 * - [ScriptedLiteRtLm]: the Galaxy A73 path (LiteRT-LM on CPU). Here it only replays text.
 * - [RecordedGeminiNano]: the documented Gemini Nano path, replaying responses and error
 *   codes. The A73 isn't on Google's supported-device list, so on that phone and in CI this
 *   path is only ever exercised through this fake.
 * Neither class touches a real model. Real backends belong in androidMain (not built yet).
 */
class ScriptedLiteRtLm(
    private val replies: List<String>,
    override val maxInputTokens: Int = 2048,
) : OnDeviceLlm {
    val prompts = mutableListOf<String>()
    override suspend fun generate(prompt: String): LlmResult {
        prompts += prompt
        return LlmResult.Text(replies.getOrElse(prompts.size - 1) { replies.last() })
    }
}

class RecordedGeminiNano(
    private val recording: List<LlmResult>,
    override val maxInputTokens: Int = 4000, // documented ML Kit prompt guidance is ~4k tokens
) : OnDeviceLlm {
    var calls = 0
        private set
    override suspend fun generate(prompt: String): LlmResult =
        recording.getOrElse(calls) { recording.last() }.also { calls++ }
}
