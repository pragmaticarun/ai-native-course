package course.m2

/**
 * The only thing commonMain knows about a model. Android backends (LiteRT-LM, ML Kit
 * Gemini Nano) implement it in androidMain; tests use fakes.
 */
interface OnDeviceLlm {
    /** Rough token count used to stay under small on-device input limits. */
    fun countTokens(prompt: String): Int = (prompt.length + 3) / 4

    /** Max input tokens this backend accepts. */
    val maxInputTokens: Int

    suspend fun generate(prompt: String): LlmResult
}

/**
 * Outcomes a backend can report. The error names mirror error codes documented for ML Kit
 * GenAI (BUSY, BACKGROUND_USE_BLOCKED, PER_APP_BATTERY_USE_QUOTA_EXCEEDED), but this is our own
 * type, not the ML Kit API.
 */
sealed interface LlmResult {
    data class Text(val text: String) : LlmResult
    data class Error(val code: ErrorCode, val message: String = code.name) : LlmResult
}

enum class ErrorCode(val retryable: Boolean) {
    BUSY(retryable = true),
    BACKGROUND_USE_BLOCKED(retryable = false),
    PER_APP_BATTERY_USE_QUOTA_EXCEEDED(retryable = false),
    UNAVAILABLE(retryable = false),
}
