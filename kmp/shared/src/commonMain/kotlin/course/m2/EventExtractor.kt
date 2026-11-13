package course.m2

import kotlinx.coroutines.delay
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json

/** M2 worked example (KMP): structured output from a notification string, on-device. */
@Serializable
data class Event(val title: String, val date: String, val location: String)

sealed interface ExtractResult {
    data class Ok(val event: Event, val modelCalls: Int) : ExtractResult
    data class Failed(val reason: String, val modelCalls: Int) : ExtractResult
}

class EventExtractor(
    private val llm: OnDeviceLlm,
    private val maxRepairs: Int = 1,
    private val maxBusyRetries: Int = 3,
    private val baseBackoffMs: Long = 200,
) {
    private val json = Json { ignoreUnknownKeys = false }

    fun prompt(notification: String): String =
        "Reply with JSON only: {\"title\": string, \"date\": \"YYYY-MM-DD\", \"location\": string}.\n" +
            "Notification: $notification"

    suspend fun extract(notification: String): ExtractResult {
        var prompt = prompt(notification)
        var calls = 0
        if (llm.countTokens(prompt) > llm.maxInputTokens) {
            return ExtractResult.Failed("input too long for this backend", calls)
        }
        repeat(maxRepairs + 1) {
            val (result, used) = generateWithBackoff(prompt)
            calls += used
            when (result) {
                is LlmResult.Error -> return ExtractResult.Failed(result.code.name, calls)
                is LlmResult.Text -> {
                    try {
                        val event = json.decodeFromString<Event>(result.text.trim())
                        if (!ISO_DATE.matches(event.date)) throw SerializationException("date must be YYYY-MM-DD")
                        return ExtractResult.Ok(event, calls)
                    } catch (e: SerializationException) {
                        // Repair: tell the model what was wrong and ask again.
                        prompt = prompt(notification) +
                            "\nYour previous reply was invalid: ${e.message?.lineSequence()?.first()}\nReturn corrected JSON."
                    } catch (e: IllegalArgumentException) {
                        prompt = prompt(notification) + "\nYour previous reply was not JSON. Return JSON only."
                    }
                }
            }
        }
        return ExtractResult.Failed("no valid JSON after ${maxRepairs + 1} attempts", calls)
    }

    /** BUSY is retryable: exponential backoff (200, 400, 800 ms by default). */
    private suspend fun generateWithBackoff(prompt: String): Pair<LlmResult, Int> {
        var calls = 0
        var delayMs = baseBackoffMs
        while (true) {
            val result = llm.generate(prompt)
            calls++
            if (result is LlmResult.Error && result.code.retryable && calls <= maxBusyRetries) {
                delay(delayMs)
                delayMs *= 2
                continue
            }
            return result to calls
        }
    }

    private companion object {
        val ISO_DATE = Regex("""\d{4}-\d{2}-\d{2}""")
    }
}
