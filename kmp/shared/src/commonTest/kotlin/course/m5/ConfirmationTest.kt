package course.m5

import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertSame

class ConfirmationTest {
    @Test
    fun deniedDeleteDoesNothing() = runTest {
        val rec = Recordings(listOf("a.m4a", "b.m4a"))
        val tools = guardDestructive(listOf(rec.list, rec.delete)) { false }
        assertSame(rec.list, tools[0]) // read-only tools are not wrapped
        val guarded = assertIs<RequiresConfirmation>(tools[1])
        assertEquals("denied by user: delete_recording was not run", guarded.invoke(mapOf("name" to "a.m4a")))
        assertEquals(listOf("a.m4a", "b.m4a"), rec.names)
        assertEquals(listOf("Allow delete_recording(name=a.m4a)?"), guarded.asked)
    }

    @Test
    fun approvedDeleteRunsOnce() = runTest {
        val rec = Recordings(listOf("a.m4a"))
        val tools = guardDestructive(listOf(rec.list, rec.delete)) { prompt -> "a.m4a" in prompt }
        assertEquals("deleted a.m4a", tools[1].invoke(mapOf("name" to "a.m4a")))
        assertEquals("", tools[0].invoke(emptyMap()))
    }
}
