package course.m4

import course.m2.ErrorCode
import course.m2.LlmResult
import course.m2.RecordedGeminiNano
import course.m2.ScriptedLiteRtLm
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class SmallWindowTest {
    private val turns = (0 until 80).map { "turn $it: " + "words ".repeat(60) }

    @Test
    fun fitsLiteRtA73WindowAndKeepsNewest() {
        val f = SmallWindow(ScriptedLiteRtLm(listOf("ok"), maxInputTokens = 2048)).fit("sys", "prefers metric", turns, "Q?")
        assertTrue(f.tokens <= 2048 - 256)
        assertTrue(f.prompt.endsWith("Q?") && "turn 79" in f.prompt && "turn 0:" !in f.prompt)
        assertTrue(f.droppedTurns > 60)
    }

    @Test
    fun nanoWindowKeepsMoreTurns() {
        val small = SmallWindow(ScriptedLiteRtLm(listOf("ok"), 2048)).fit("s", "", turns, "q")
        val nano = SmallWindow(RecordedGeminiNano(listOf(LlmResult.Text("ok")))).fit("s", "", turns, "q")
        assertTrue(nano.droppedTurns < small.droppedTurns)
    }

    @Test
    fun oversizedSummaryIsRejected() {
        assertFailsWith<IllegalArgumentException> {
            SmallWindow(ScriptedLiteRtLm(listOf("ok"), 2048)).fit("s", "m ".repeat(5000), emptyList(), "q")
        }
    }

    @Test
    fun summaryUpdateKeepsOldMemoryOnError() = runTest {
        val busy = RecordedGeminiNano(listOf(LlmResult.Error(ErrorCode.PER_APP_BATTERY_USE_QUOTA_EXCEEDED)))
        assertEquals("old", SmallWindow(busy).updateSummary("old", listOf("x")))
        val lite = ScriptedLiteRtLm(listOf("new memory"))
        assertEquals("new memory", SmallWindow(lite).updateSummary("old", listOf("x")))
        assertEquals("old", SmallWindow(lite).updateSummary("old", emptyList()))
    }
}
