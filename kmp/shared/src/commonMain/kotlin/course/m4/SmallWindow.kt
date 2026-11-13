package course.m4

import course.m2.OnDeviceLlm

/**
 * M4 (c), Kotlin: fit a prompt + history into a small on-device window with a running
 * summary as memory. Window sizes: 2,048 tokens is what we configure for LiteRT-LM on the
 * Galaxy A73; ~4,000 is ML Kit Prompt API's documented input guidance for Gemini Nano.
 */
data class Fitted(val prompt: String, val droppedTurns: Int, val tokens: Int)

class SmallWindow(private val llm: OnDeviceLlm, private val reserveOutput: Int = 256) {
    fun fit(system: String, summary: String, turns: List<String>, question: String): Fitted {
        val budget = llm.maxInputTokens - reserveOutput
        val memory = if (summary.isBlank()) "" else "Memory: $summary"
        var used = listOf(system, memory, question).sumOf { llm.countTokens(it) }
        require(used <= budget) { "system + summary + question exceed the window; shorten the summary" }
        val kept = ArrayDeque<String>()
        for (turn in turns.asReversed()) {
            val cost = llm.countTokens(turn)
            if (used + cost > budget) break
            kept.addFirst(turn)
            used += cost
        }
        val prompt = (listOf(system, memory) + kept + question).filter { it.isNotEmpty() }.joinToString("\n")
        return Fitted(prompt, turns.size - kept.size, used)
    }

    /** When turns are dropped, fold them into the summary (the model writes it; tests fake it). */
    suspend fun updateSummary(summary: String, dropped: List<String>): String {
        if (dropped.isEmpty()) return summary
        val prompt = "Update this memory in under 60 words.\nMemory: $summary\nNew: ${dropped.joinToString(" | ")}"
        return when (val r = llm.generate(prompt.take(llm.maxInputTokens * 4))) {
            is course.m2.LlmResult.Text -> r.text.trim()
            is course.m2.LlmResult.Error -> summary // keep the old memory rather than lose it
        }
    }
}
