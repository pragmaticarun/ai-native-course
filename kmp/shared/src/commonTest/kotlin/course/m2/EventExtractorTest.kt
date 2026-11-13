package course.m2

import kotlinx.coroutines.test.currentTime
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertTrue

@OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
class EventExtractorTest {
    private val good = """{"title": "Rust meetup", "date": "2026-11-20", "location": "Bengaluru"}"""
    private val notification = "Rust meetup on 20 Nov 2026 at Bengaluru"

    @Test
    fun liteRtPathParsesFirstTry() = runTest {
        val result = EventExtractor(ScriptedLiteRtLm(listOf(good))).extract(notification)
        assertEquals(ExtractResult.Ok(Event("Rust meetup", "2026-11-20", "Bengaluru"), 1), result)
    }

    @Test
    fun repairsMissingFieldOnce() = runTest {
        val llm = ScriptedLiteRtLm(listOf("""{"title": "Rust meetup", "date": "2026-11-20"}""", good))
        val result = EventExtractor(llm).extract(notification)
        assertIs<ExtractResult.Ok>(result)
        assertEquals(2, result.modelCalls)
        assertTrue("invalid" in llm.prompts[1])
    }

    @Test
    fun rejectsNonIsoDateThenGivesUp() = runTest {
        val bad = """{"title": "x", "date": "20/11/2026", "location": "y"}"""
        val result = EventExtractor(ScriptedLiteRtLm(listOf(bad))).extract(notification)
        assertIs<ExtractResult.Failed>(result)
        assertEquals(2, result.modelCalls)
    }

    @Test
    fun nanoBusyIsRetriedWithExponentialBackoff() = runTest {
        val nano = RecordedGeminiNano(
            listOf(LlmResult.Error(ErrorCode.BUSY), LlmResult.Error(ErrorCode.BUSY), LlmResult.Text(good)),
        )
        val result = EventExtractor(nano).extract(notification)
        assertIs<ExtractResult.Ok>(result)
        assertEquals(3, nano.calls)
        assertEquals(200L + 400L, currentTime) // virtual time: 200 ms then 400 ms
    }

    @Test
    fun nanoBackgroundBlockIsNotRetried() = runTest {
        val nano = RecordedGeminiNano(listOf(LlmResult.Error(ErrorCode.BACKGROUND_USE_BLOCKED)))
        assertEquals(ExtractResult.Failed("BACKGROUND_USE_BLOCKED", 1), EventExtractor(nano).extract(notification))
    }

    @Test
    fun inputLimitIsCheckedBeforeCallingTheModel() = runTest {
        val nano = RecordedGeminiNano(listOf(LlmResult.Text(good)), maxInputTokens = 10)
        val result = EventExtractor(nano).extract(notification)
        assertIs<ExtractResult.Failed>(result)
        assertEquals(0, nano.calls)
    }
}
